"""
Implementa los nodos de firmas geológicas y ensamblado de la matriz de modelado.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def fit_geological_signatures(
    geology_composition_daily: pd.DataFrame,
    geology_clustering: dict,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """
    Selecciona el número de firmas por silueta usando únicamente la historia de entrenamiento.

    Parámetros:
    -------------
    geology_composition_daily : composiciones geológicas diarias ordenables por fecha.
    geology_clustering : configuración temporal y de hiperparámetros para ``KMeans``.

    Retorna:
    ---------
    tuple[pd.DataFrame, dict[str, Any], pd.DataFrame] : firmas diarias, artefacto ajustado y
    diagnóstico de silueta para cada número de clusters evaluado.
    """
    df = geology_composition_daily.sort_values("date").copy()
    feature_cols = [column for column in df if column.startswith(("lithology_", "quality_"))]
    training_end = pd.Timestamp(geology_clustering["training_end"])
    train_mask = df["date"].le(training_end)
    scaler = StandardScaler().fit(df.loc[train_mask, feature_cols])
    train_scaled = scaler.transform(df.loc[train_mask, feature_cols])
    full_scaled = scaler.transform(df[feature_cols])

    diagnostics: list[dict[str, float]] = []
    candidates: dict[int, KMeans] = {}
    for n_clusters in range(
        int(geology_clustering["min_clusters"]),
        int(geology_clustering["max_clusters"]) + 1,
    ):
        model = KMeans(
            n_clusters=n_clusters,
            random_state=int(geology_clustering["random_seed"]),
            n_init=20,
            max_iter=400,
        )
        labels = model.fit_predict(train_scaled)
        score = float(silhouette_score(train_scaled, labels))
        diagnostics.append({"n_clusters": n_clusters, "silhouette_score": score})
        candidates[n_clusters] = model

    diagnostics_df = pd.DataFrame(diagnostics).sort_values("n_clusters")
    best_k = int(diagnostics_df.loc[diagnostics_df["silhouette_score"].idxmax(), "n_clusters"])
    best_model = candidates[best_k]
    signature_df = df[["date"]].copy()
    signature_df["geological_signature"] = [
        f"SIGNATURE_{label + 1:02d}" for label in best_model.predict(full_scaled)
    ]
    artifact = {
        "feature_columns": feature_cols,
        "training_end": str(training_end.date()),
        "best_k": best_k,
        "scaler": scaler,
        "model": best_model,
    }
    return signature_df, artifact, diagnostics_df


def assemble_model_input(
    plant_target_daily: pd.DataFrame,
    plant_context_daily: pd.DataFrame,
    geological_signatures_daily: pd.DataFrame,
    spatial_context_daily: pd.DataFrame,
    analysis: dict,
    spatial: dict,
    bayesian: dict,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Construye el contrato diario que separa variables, objetivo y metadatos temporales.

    Parámetros:
    -------------
    plant_target_daily : rendimiento diario observado de la planta.
    plant_context_daily : condiciones operacionales agregadas por día.
    geological_signatures_daily : firma geológica asignada a cada fecha.
    spatial_context_daily : procedencias y dureza agregadas por día.
    analysis : límites temporales del análisis y de la evaluación.
    spatial : umbrales mínimos de soporte espacial.
    bayesian : configuración de las variables regulares del modelo.

    Retorna:
    ---------
    tuple[pd.DataFrame, dict[str, Any]] : matriz diaria modelable y descripción de su esquema.
    """
    df = (
        plant_target_daily.merge(plant_context_daily, on="date", how="inner")
        .merge(geological_signatures_daily, on="date", how="inner")
        .merge(spatial_context_daily, on="date", how="inner")
        .sort_values("date")
        .reset_index(drop=True)
    )
    share_cols = sorted(
        column
        for column in df
        if column.startswith("zone_share__") or column.startswith("hardness_share__")
    )
    df[share_cols] = df[share_cols].fillna(0.0)
    training_end = pd.Timestamp(analysis["training_end"])
    fines_center = float(df.loc[df["date"].le(training_end), "feed_fines_pct_mean"].mean())
    df["feed_fines_pct_centered_sq"] = (df["feed_fines_pct_mean"] - fines_center) ** 2

    required = [
        "plant_total_tph",
        "geological_signature",
        "n_feed_cycles",
        *bayesian["regular_features"],
    ]
    df = (
        df.dropna(subset=required)
        .loc[lambda frame: frame["n_feed_cycles"].ge(spatial["min_cycles_per_day"])]
        .loc[lambda frame: frame["date"].le(pd.Timestamp(analysis["evaluation_end"]))]
        .reset_index(drop=True)
    )
    schema = {
        "grain": "one row per calendar day",
        "target": "plant_total_tph",
        "signature": "geological_signature",
        "regular_features": list(bayesian["regular_features"]),
        "zone_share_features": [
            column for column in share_cols if column.startswith("zone_share__")
        ],
        "hardness_share_features": [
            column for column in share_cols if column.startswith("hardness_share__")
        ],
        "support_only": ["n_feed_cycles", "hardness_match_pct"],
        "fines_center_training_only": fines_center,
        "date_min": str(df["date"].min().date()),
        "date_max": str(df["date"].max().date()),
        "n_rows": int(len(df)),
    }
    return df, schema
