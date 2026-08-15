"""
Implementa el modelo jerárquico, el posterior predictivo y el backtesting temporal móvil.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt
import statsmodels.api as sm
from sklearn.metrics import mean_absolute_error, mean_squared_error


@dataclass
class StandardizedFamily:
    """
    Conserva matrices estandarizadas y la transformación ajustada solo en entrenamiento.

    Parámetros:
    -------------
    train : matriz estandarizada del período de entrenamiento.
    prediction : matriz estandarizada del período que se desea predecir.
    mean : medias de entrenamiento usadas para centrar las variables.
    std : desviaciones de entrenamiento usadas para escalar las variables.
    """

    train: np.ndarray
    prediction: np.ndarray
    mean: pd.Series
    std: pd.Series


def _standardize(train: pd.DataFrame, prediction: pd.DataFrame) -> StandardizedFamily:
    """
    Estandariza entrenamiento y predicción con estadísticas calculadas solo en entrenamiento.

    Parámetros:
    -------------
    train : variables del período de ajuste.
    prediction : variables del período que se desea transformar.

    Retorna:
    ---------
    StandardizedFamily : matrices transformadas junto con sus medias y desviaciones.
    """
    mean = train.mean(axis=0)
    std = train.std(axis=0).replace(0, 1.0).fillna(1.0)
    return StandardizedFamily(
        train=((train - mean) / std).to_numpy(dtype=float),
        prediction=((prediction - mean) / std).to_numpy(dtype=float),
        mean=mean,
        std=std,
    )


def _select_compositional_features(
    train_df: pd.DataFrame,
    prefix: str,
    min_mean_share_pct: float,
    preferred_reference: str | None = None,
    excluded_suffix: str | None = None,
) -> tuple[list[str], str]:
    """
    Selecciona componentes composicionales con soporte suficiente y fija una referencia.

    Parámetros:
    -------------
    train_df : matriz diaria disponible durante el entrenamiento.
    prefix : prefijo que identifica la familia composicional.
    min_mean_share_pct : participación media mínima exigida para conservar un componente.
    preferred_reference : componente de referencia preferido cuando está disponible.
    excluded_suffix : sufijo opcional que excluye componentes de la selección.

    Retorna:
    ---------
    tuple[list[str], str] : componentes seleccionados y nombre de la referencia.
    """
    candidates = sorted(column for column in train_df if column.startswith(prefix))
    if not candidates:
        raise ValueError(f"No existen columnas composicionales con prefijo {prefix!r}.")
    mean_share = train_df[candidates].mean().sort_values(ascending=False)
    reference = (
        preferred_reference if preferred_reference in candidates else str(mean_share.index[0])
    )
    selected = [
        column
        for column, share in mean_share.items()
        if share >= min_mean_share_pct
        and column != reference
        and (excluded_suffix is None or not column.endswith(excluded_suffix))
    ]
    return selected, reference


def _empirical_regular_priors(
    y_train: np.ndarray,
    regular: StandardizedFamily,
    zone: StandardizedFamily,
    hardness: StandardizedFamily,
    regular_features: list[str],
    zone_features: list[str],
    hardness_features: list[str],
    signatures: pd.Series,
    hac_maxlags: int,
    prior_std_multiplier: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Deriva priors regulares desde un modelo OLS completo con errores HAC.

    Parámetros:
    -------------
    y_train : rendimiento observado durante el entrenamiento.
    regular : familia estandarizada de variables operacionales regulares.
    zone : familia estandarizada de composiciones de procedencia.
    hardness : familia estandarizada de composiciones de dureza.
    regular_features : nombres de las variables operacionales regulares.
    zone_features : nombres de las composiciones de procedencia.
    hardness_features : nombres de las composiciones de dureza.
    signatures : firmas geológicas observadas durante el entrenamiento.
    hac_maxlags : rezago máximo usado por la covarianza HAC.
    prior_std_multiplier : multiplicador aplicado al error robusto de cada coeficiente.

    Retorna:
    ---------
    tuple[np.ndarray, np.ndarray, float] : medias y desviaciones de los priors, más la
    desviación residual estimada por OLS.
    """
    frames = [pd.DataFrame(regular.train, columns=regular_features)]
    if zone_features:
        frames.append(pd.DataFrame(zone.train, columns=zone_features))
    if hardness_features:
        frames.append(pd.DataFrame(hardness.train, columns=hardness_features))
    frames.append(
        pd.get_dummies(
            signatures.reset_index(drop=True), prefix="signature", drop_first=True, dtype=float
        )
    )
    design = sm.add_constant(pd.concat(frames, axis=1), has_constant="add")
    ols = sm.OLS(y_train, design).fit()
    robust = ols.get_robustcov_results(cov_type="HAC", maxlags=hac_maxlags)
    robust_lookup = pd.Series(robust.bse, index=ols.params.index)
    prior_mean = ols.params.reindex(regular_features).fillna(0.0).to_numpy(dtype=float)
    prior_std = prior_std_multiplier * robust_lookup.reindex(regular_features).fillna(
        100.0
    ).to_numpy(dtype=float)
    prior_std = np.maximum(
        np.where(np.isfinite(prior_std) & (prior_std > 0), prior_std, 100.0),
        1.0,
    )
    sigma_hat = float(np.sqrt(ols.mse_resid))
    return prior_mean, prior_std, sigma_hat


def _posterior_matrix(idata: Any, variable: str, dimension: str) -> np.ndarray:
    """
    Reordena una variable posterior como una matriz de dimensión por muestra.

    Parámetros:
    -------------
    idata : objeto de inferencia que contiene las cadenas posteriores.
    variable : nombre de la variable posterior que se desea extraer.
    dimension : dimensión de coordenadas que debe ocupar las filas.

    Retorna:
    ---------
    np.ndarray : matriz con la dimensión solicitada en filas y las muestras en columnas.
    """
    return (
        idata.posterior[variable]
        .stack(sample=("chain", "draw"))
        .transpose(dimension, "sample")
        .to_numpy()
    )


def fit_hierarchical_model(
    train_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    bayesian: dict,
    features: dict,
    sampling: dict,
    random_seed: int,
) -> tuple[Any, pd.DataFrame, dict[str, Any]]:
    """
    Ajusta una especificación jerárquica identificable y predice media y observación futura.

    Parámetros:
    -------------
    train_df : observaciones diarias usadas para ajustar el modelo.
    prediction_df : observaciones cuyo rendimiento se desea explicar o predecir.
    bayesian : variables, escalas de priors y configuración general del modelo.
    features : umbrales para seleccionar composiciones de procedencia y dureza.
    sampling : argumentos entregados a ``pymc.sample``.
    random_seed : semilla que controla muestreo y simulación posterior predictiva.

    Retorna:
    ---------
    tuple[Any, pd.DataFrame, dict[str, Any]] : inferencia posterior, predicciones con
    contribuciones y metadatos de la especificación ajustada.
    """
    train_df = train_df.sort_values("date").reset_index(drop=True)
    prediction_df = prediction_df.sort_values("date").reset_index(drop=True)
    regular_features = list(bayesian["regular_features"])
    zone_features, zone_reference = _select_compositional_features(
        train_df,
        "zone_share__",
        features["min_zone_mean_share_pct"],
    )
    hardness_features, hardness_reference = _select_compositional_features(
        train_df,
        "hardness_share__",
        features["min_hardness_mean_share_pct"],
        preferred_reference=features["hardness_reference"],
        excluded_suffix="unmatched",
    )

    regular = _standardize(
        train_df[regular_features].astype(float), prediction_df[regular_features].astype(float)
    )
    zone = _standardize(
        train_df[zone_features].astype(float), prediction_df[zone_features].astype(float)
    )
    hardness = _standardize(
        train_df[hardness_features].astype(float), prediction_df[hardness_features].astype(float)
    )

    signature_categories = pd.Index(
        sorted(
            pd.concat(
                [train_df["geological_signature"], prediction_df["geological_signature"]],
                ignore_index=True,
            ).unique()
        ),
        name="signature",
    )
    signature_lookup = {value: index for index, value in enumerate(signature_categories)}
    train_signature_index = (
        train_df["geological_signature"].map(signature_lookup).to_numpy(dtype=int)
    )
    prediction_signature_index = (
        prediction_df["geological_signature"].map(signature_lookup).to_numpy(dtype=int)
    )
    y_train = train_df["plant_total_tph"].to_numpy(dtype=float)

    regular_prior_mean, regular_prior_std, sigma_hat = _empirical_regular_priors(
        y_train=y_train,
        regular=regular,
        zone=zone,
        hardness=hardness,
        regular_features=regular_features,
        zone_features=zone_features,
        hardness_features=hardness_features,
        signatures=train_df["geological_signature"],
        hac_maxlags=int(bayesian["hac_maxlags"]),
        prior_std_multiplier=float(bayesian["prior_std_multiplier"]),
    )

    coords = {
        "regular_feature": regular_features,
        "zone_feature": zone_features,
        "hardness_feature": hardness_features,
        "signature": signature_categories.tolist(),
        "obs_train": np.arange(len(train_df)),
        "obs_prediction": np.arange(len(prediction_df)),
    }
    with pm.Model(coords=coords):
        regular_train_data = pm.Data(
            "regular_train", regular.train, dims=("obs_train", "regular_feature")
        )
        regular_prediction_data = pm.Data(
            "regular_prediction", regular.prediction, dims=("obs_prediction", "regular_feature")
        )
        zone_train_data = pm.Data("zone_train", zone.train, dims=("obs_train", "zone_feature"))
        zone_prediction_data = pm.Data(
            "zone_prediction", zone.prediction, dims=("obs_prediction", "zone_feature")
        )
        hardness_train_data = pm.Data(
            "hardness_train", hardness.train, dims=("obs_train", "hardness_feature")
        )
        hardness_prediction_data = pm.Data(
            "hardness_prediction", hardness.prediction, dims=("obs_prediction", "hardness_feature")
        )
        train_signature_data = pm.Data(
            "train_signature_index", train_signature_index, dims="obs_train"
        )
        prediction_signature_data = pm.Data(
            "prediction_signature_index", prediction_signature_index, dims="obs_prediction"
        )

        alpha = pm.Normal(
            "alpha", mu=float(y_train.mean()), sigma=float(max(y_train.std(), sigma_hat))
        )
        beta_regular = pm.Normal(
            "beta_regular",
            mu=regular_prior_mean,
            sigma=regular_prior_std,
            dims="regular_feature",
        )
        sigma_zone = pm.HalfNormal("sigma_zone", sigma=bayesian["zone_scale_prior_tph"])
        beta_zone = pm.Deterministic(
            "beta_zone",
            pm.Normal("zone_offset", 0.0, 1.0, dims="zone_feature") * sigma_zone,
            dims="zone_feature",
        )
        sigma_hardness = pm.HalfNormal("sigma_hardness", sigma=bayesian["hardness_scale_prior_tph"])
        beta_hardness = pm.Deterministic(
            "beta_hardness",
            pm.Normal("hardness_offset", 0.0, 1.0, dims="hardness_feature") * sigma_hardness,
            dims="hardness_feature",
        )
        sigma_signature = pm.HalfNormal(
            "sigma_signature", sigma=bayesian["cluster_scale_prior_tph"]
        )
        signature_raw = pm.Normal("signature_raw", 0.0, 1.0, dims="signature")
        signature_effect = pm.Deterministic(
            "signature_effect",
            (signature_raw - pt.mean(signature_raw)) * sigma_signature,
            dims="signature",
        )
        sigma_observation = pm.HalfNormal("sigma_observation", sigma=max(sigma_hat, 1.0))

        mu_train = alpha + pm.math.dot(regular_train_data, beta_regular)
        mu_prediction = alpha + pm.math.dot(regular_prediction_data, beta_regular)
        if zone_features:
            mu_train = mu_train + pm.math.dot(zone_train_data, beta_zone)
            mu_prediction = mu_prediction + pm.math.dot(zone_prediction_data, beta_zone)
        if hardness_features:
            mu_train = mu_train + pm.math.dot(hardness_train_data, beta_hardness)
            mu_prediction = mu_prediction + pm.math.dot(hardness_prediction_data, beta_hardness)
        mu_train = pm.Deterministic(
            "mu_train", mu_train + signature_effect[train_signature_data], dims="obs_train"
        )
        pm.Deterministic(
            "mu_prediction",
            mu_prediction + signature_effect[prediction_signature_data],
            dims="obs_prediction",
        )
        pm.Normal(
            "observed_tph", mu=mu_train, sigma=sigma_observation, observed=y_train, dims="obs_train"
        )
        idata = pm.sample(
            **sampling,
            random_seed=random_seed,
            return_inferencedata=True,
        )

    mu_draws = _posterior_matrix(idata, "mu_prediction", "obs_prediction")
    sigma_draws = np.asarray(idata.posterior["sigma_observation"]).reshape(-1)
    rng = np.random.default_rng(random_seed + 10_000)
    predictive_draws = mu_draws + rng.normal(size=mu_draws.shape) * sigma_draws[None, :]
    mu_quantiles = np.quantile(mu_draws, [0.05, 0.5, 0.95], axis=1)
    predictive_quantiles = np.quantile(predictive_draws, [0.05, 0.5, 0.95], axis=1)

    beta_regular_draws = _posterior_matrix(idata, "beta_regular", "regular_feature")
    signature_draws = _posterior_matrix(idata, "signature_effect", "signature")
    beta_zone_draws = _posterior_matrix(idata, "beta_zone", "zone_feature")
    beta_hardness_draws = _posterior_matrix(idata, "beta_hardness", "hardness_feature")
    alpha_mean = float(np.asarray(idata.posterior["alpha"]).mean())

    prediction = prediction_df[["date", "plant_total_tph", "geological_signature"]].copy()
    prediction["y_true"] = prediction["plant_total_tph"]
    prediction["y_pred_mean"] = mu_draws.mean(axis=1)
    prediction["mean_p05"] = mu_quantiles[0]
    prediction["mean_p50"] = mu_quantiles[1]
    prediction["mean_p95"] = mu_quantiles[2]
    prediction["predictive_p05"] = predictive_quantiles[0]
    prediction["predictive_p50"] = predictive_quantiles[1]
    prediction["predictive_p95"] = predictive_quantiles[2]
    prediction["base_component"] = alpha_mean
    prediction["contrib_geology"] = signature_draws[prediction_signature_index].mean(axis=1)
    for index, feature in enumerate(regular_features):
        prediction[f"contrib__{feature}"] = (
            regular.prediction[:, index, None] * beta_regular_draws[index][None, :]
        ).mean(axis=1)
    prediction["contrib_source"] = (
        (zone.prediction @ beta_zone_draws).mean(axis=1) if zone_features else 0.0
    )
    prediction["contrib_hardness_mix"] = (
        (hardness.prediction @ beta_hardness_draws).mean(axis=1) if hardness_features else 0.0
    )
    prediction["residual_actual_minus_model"] = prediction["y_true"] - prediction["y_pred_mean"]

    metadata = {
        "regular_features": regular_features,
        "zone_features": zone_features,
        "hardness_features": hardness_features,
        "zone_reference": zone_reference,
        "hardness_reference": hardness_reference,
        "signature_categories": signature_categories.tolist(),
        "n_divergences": int(idata.sample_stats["diverging"].sum().values),
    }
    return idata, prediction, metadata


def _metrics(prediction: pd.DataFrame) -> dict[str, float]:
    """
    Calcula métricas puntuales y coberturas de intervalos para un conjunto de predicciones.

    Parámetros:
    -------------
    prediction : valores observados, predichos e intervalos posteriores por día.

    Retorna:
    ---------
    dict[str, float] : tamaño de muestra, errores, sesgo y coberturas de intervalos al 90 %.
    """
    y_true = prediction["y_true"].to_numpy()
    y_pred = prediction["y_pred_mean"].to_numpy()
    return {
        "n_days": len(prediction),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "bias_pred_minus_actual": float(np.mean(y_pred - y_true)),
        "mean_interval_90_coverage_pct": float(
            100 * ((y_true >= prediction["mean_p05"]) & (y_true <= prediction["mean_p95"])).mean()
        ),
        "predictive_interval_90_coverage_pct": float(
            100
            * (
                (y_true >= prediction["predictive_p05"]) & (y_true <= prediction["predictive_p95"])
            ).mean()
        ),
    }


def run_rolling_backtest(
    model_input_daily: pd.DataFrame,
    bayesian: dict,
    features: dict,
    backtest: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta la política de ventana móvil seleccionada y concatena sus resultados fuera de muestra.

    Parámetros:
    -------------
    model_input_daily : contrato diario completo ordenable por fecha.
    bayesian : configuración del modelo y semilla base.
    features : umbrales de selección de familias composicionales.
    backtest : ventanas, horizonte, soportes mínimos y configuración de muestreo.

    Retorna:
    ---------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] : predicciones diarias, métricas por fold
    y resumen agregado de la política móvil.
    """
    df = model_input_daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    start = pd.Timestamp(backtest["start"])
    end = min(pd.Timestamp(backtest["end"]), df["date"].max() + pd.Timedelta(days=1))
    fold_starts = pd.date_range(
        start, end - pd.Timedelta(days=1), freq=f"{backtest['step_months']}MS"
    )
    predictions: list[pd.DataFrame] = []
    metrics: list[dict[str, Any]] = []

    for fold_id, fold_start in enumerate(fold_starts, start=1):
        fold_end = min(fold_start + pd.DateOffset(months=backtest["horizon_months"]), end)
        train_start = fold_start - pd.DateOffset(months=backtest["rolling_train_months"])
        train = df.loc[df["date"].ge(train_start) & df["date"].lt(fold_start)].copy()
        test = df.loc[df["date"].ge(fold_start) & df["date"].lt(fold_end)].copy()
        if len(train) < backtest["min_train_days"] or len(test) < backtest["min_test_days"]:
            continue
        idata, fold_prediction, metadata = fit_hierarchical_model(
            train,
            test,
            bayesian=bayesian,
            features=features,
            sampling=backtest["sampling"],
            random_seed=int(bayesian["random_seed"]) + fold_id,
        )
        fold_prediction["fold_id"] = fold_id
        fold_prediction["fold_start"] = fold_start
        fold_prediction["fold_end"] = fold_end
        fold_prediction["train_start"] = train["date"].min()
        fold_prediction["train_end"] = train["date"].max()
        predictions.append(fold_prediction)
        metrics.append(
            {
                "fold_id": fold_id,
                "fold_start": fold_start,
                "fold_end": fold_end,
                "train_start": train["date"].min(),
                "train_end": train["date"].max(),
                "n_train": len(train),
                "n_test": len(test),
                "n_zone_features": len(metadata["zone_features"]),
                "n_hardness_features": len(metadata["hardness_features"]),
                "n_divergences": metadata["n_divergences"],
                **_metrics(fold_prediction),
            }
        )
        del idata

    if not predictions:
        raise ValueError("La configuración temporal no produjo folds válidos.")
    prediction_df = pd.concat(predictions, ignore_index=True)
    fold_metrics_df = pd.DataFrame(metrics)
    summary_df = pd.DataFrame([{"policy": "rolling_12m", **_metrics(prediction_df)}])
    summary_df["n_divergences"] = int(fold_metrics_df["n_divergences"].sum())
    return prediction_df, fold_metrics_df, summary_df


def fit_final_model(
    model_input_daily: pd.DataFrame,
    bayesian: dict,
    features: dict,
) -> tuple[Any, pd.DataFrame]:
    """
    Ajusta el posterior final sobre todo el historial publicado.

    Parámetros:
    -------------
    model_input_daily : contrato diario completo usado para el ajuste final.
    bayesian : variables, priors, muestreo y semilla del modelo.
    features : umbrales de selección de composiciones de procedencia y dureza.

    Retorna:
    ---------
    tuple[Any, pd.DataFrame] : objeto de inferencia final y resumen tabular de parámetros.
    """
    idata, _, _ = fit_hierarchical_model(
        model_input_daily,
        model_input_daily,
        bayesian=bayesian,
        features=features,
        sampling=bayesian["sampling"],
        random_seed=int(bayesian["random_seed"]),
    )
    summary = az.summary(
        idata,
        var_names=[
            "alpha",
            "beta_regular",
            "beta_zone",
            "beta_hardness",
            "signature_effect",
            "sigma_observation",
        ],
        hdi_prob=0.90,
    ).reset_index(names="parameter")
    return idata, summary
