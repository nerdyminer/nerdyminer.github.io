"""
Implementa nodos puros que convierten extractos estáticos en entidades diarias de negocio.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from matplotlib.path import Path as PolygonPath
from scipy.spatial import ConvexHull, QhullError, cKDTree
from sklearn.cluster import DBSCAN

PLANT_SIGNAL_COLUMNS = [
    "line_a_feed_tph",
    "line_b_feed_tph",
    "line_a_power_kw",
    "line_b_power_kw",
    "intermediate_stockpile_level_m",
    "line_a_discharge_sump_pct",
    "line_b_discharge_sump_pct",
    "feed_fines_pct",
    "auxiliary_crusher_1_state",
    "auxiliary_crusher_2_state",
    "auxiliary_crusher_3_state",
    "line_a_pump_1_state",
    "line_a_pump_2_state",
    "line_a_pump_3_state",
    "line_b_pump_1_state",
    "line_b_pump_2_state",
    "line_b_pump_3_state",
    "line_a_ball_mill_1_state",
    "line_a_ball_mill_2_state",
    "line_b_ball_mill_1_state",
    "line_b_ball_mill_2_state",
]


def _require_columns(df: pd.DataFrame, required: list[str], dataset_name: str) -> None:
    """
    Verifica que un dataframe contenga todas las columnas exigidas por su contrato.

    Parámetros:
    -------------
    df : dataframe que se desea validar.
    required : nombres de las columnas obligatorias.
    dataset_name : nombre legible del dataset usado en el mensaje de error.

    Retorna:
    ---------
    None. La función levanta ``ValueError`` cuando falta alguna columna.
    """
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{dataset_name} no cumple su contrato; faltan columnas: {missing}")


def clean_plant_signals(plant_signals_hourly_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Valida tipos, orden temporal y unicidad de las señales horarias de planta.

    Parámetros:
    -------------
    plant_signals_hourly_raw : extracto horario sin normalizar de señales de planta.

    Retorna:
    ---------
    pd.DataFrame : señales seleccionadas, tipadas, deduplicadas y ordenadas por tiempo.
    """
    required = ["timestamp", *PLANT_SIGNAL_COLUMNS]
    _require_columns(plant_signals_hourly_raw, required, "plant_signals_hourly_raw")
    df = plant_signals_hourly_raw[required].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    for column in PLANT_SIGNAL_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return (
        df.drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)
    )


def build_daily_plant_tables(
    plant_signals_hourly_clean: pd.DataFrame,
    plant: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Construye el objetivo diario y las condiciones contextuales del circuito didáctico.

    Parámetros:
    -------------
    plant_signals_hourly_clean : señales horarias limpias de ambas líneas de molienda.
    plant : umbrales operacionales para estabilidad y disponibilidad de equipos.

    Retorna:
    ---------
    tuple[pd.DataFrame, pd.DataFrame] : rendimiento diario y contexto operacional diario.
    """
    df = plant_signals_hourly_clean.copy()
    df["date"] = df["timestamp"].dt.normalize()
    online_threshold = float(plant["online_threshold"])

    line_a_stable = df["line_a_feed_tph"].ge(plant["stable_feed_min_tph"]) & df[
        "line_a_power_kw"
    ].ge(plant["stable_power_min_kw"])
    line_b_stable = df["line_b_feed_tph"].ge(plant["stable_feed_min_tph"]) & df[
        "line_b_power_kw"
    ].ge(plant["stable_power_min_kw"])
    line_a_daily = df["line_a_feed_tph"].where(line_a_stable).groupby(df["date"]).mean()
    line_b_daily = df["line_b_feed_tph"].where(line_b_stable).groupby(df["date"]).mean()
    target_df = pd.concat(
        [line_a_daily.rename("line_a_tph"), line_b_daily.rename("line_b_tph")], axis=1
    ).reset_index()
    target_df["plant_total_tph"] = target_df["line_a_tph"] + target_df["line_b_tph"]

    upstream_available = df["intermediate_stockpile_level_m"].gt(
        plant["intermediate_stockpile_min_m"]
    )
    low_sump, high_sump = plant["discharge_sump_range_pct"]
    sumps_in_range = df["line_a_discharge_sump_pct"].between(low_sump, high_sump) & df[
        "line_b_discharge_sump_pct"
    ].between(low_sump, high_sump)
    auxiliary_crushing_available = (
        df[["auxiliary_crusher_1_state", "auxiliary_crusher_2_state", "auxiliary_crusher_3_state"]]
        .ge(online_threshold)
        .any(axis=1)
    )

    phase_availability: list[pd.Series] = []
    for line in ("a", "b"):
        pumps_online = (
            df[
                [
                    f"line_{line}_pump_1_state",
                    f"line_{line}_pump_2_state",
                    f"line_{line}_pump_3_state",
                ]
            ]
            .ge(online_threshold)
            .sum(axis=1)
        )
        mills_online = (
            df[[f"line_{line}_ball_mill_1_state", f"line_{line}_ball_mill_2_state"]]
            .ge(online_threshold)
            .all(axis=1)
        )
        phase_availability.append(pumps_online.ge(2) & mills_online)
    secondary_available = pd.concat(phase_availability, axis=1).mean(axis=1)

    hourly_context = pd.DataFrame(
        {
            "date": df["date"],
            "upstream_available": upstream_available.astype(float),
            "discharge_sumps_in_range": sumps_in_range.astype(float),
            "auxiliary_crushing_available": auxiliary_crushing_available.astype(float),
            "secondary_grinding_available": secondary_available,
            "feed_fines_pct": df["feed_fines_pct"].where(df["feed_fines_pct"].between(0, 100)),
        }
    )
    context_df = hourly_context.groupby("date", as_index=False).agg(
        upstream_available_pct=("upstream_available", lambda x: 100 * x.mean()),
        discharge_sumps_in_range_pct=("discharge_sumps_in_range", lambda x: 100 * x.mean()),
        auxiliary_crushing_available_pct=("auxiliary_crushing_available", lambda x: 100 * x.mean()),
        secondary_grinding_available_pct=("secondary_grinding_available", lambda x: 100 * x.mean()),
        feed_fines_pct_mean=("feed_fines_pct", "mean"),
    )
    return target_df, context_df


def build_geology_composition(geology_daily_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte tonelajes diarios de litología y calidad en composiciones cerradas.

    Parámetros:
    -------------
    geology_daily_raw : tonelajes y variables de calidad informados por día.

    Retorna:
    ---------
    pd.DataFrame : proporciones geológicas y de calidad válidas, ordenadas por fecha.
    """
    df = geology_daily_raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    lithology_cols = sorted(column for column in df if column.startswith("lithology_"))
    quality_cols = sorted(column for column in df if column.startswith("quality_"))
    _require_columns(
        df, ["date", "feed_tonnes", *lithology_cols, *quality_cols], "geology_daily_raw"
    )
    denominator = pd.to_numeric(df["feed_tonnes"], errors="coerce").replace(0, np.nan)
    for column in [*lithology_cols, *quality_cols]:
        df[column] = pd.to_numeric(df[column], errors="coerce") / denominator
    return df[["date", *lithology_cols, *quality_cols]].dropna().sort_values("date")


def enrich_haulage_with_hardness(
    haulage_cycles_raw: pd.DataFrame,
    hardness_block_model_raw: pd.DataFrame,
    spatial: dict,
) -> pd.DataFrame:
    """
    Asocia cada punto de carguío sintético al bloque de dureza más cercano.

    Parámetros:
    -------------
    haulage_cycles_raw : ciclos de transporte con origen, destino y coordenadas de carguío.
    hardness_block_model_raw : bloques espaciales con penetración y clase de dureza.
    spatial : tolerancias y parámetros del emparejamiento espacial.

    Retorna:
    ---------
    pd.DataFrame : ciclos destinados al chancador primario enriquecidos con dureza y procedencia.
    """
    cycle_cols = [
        "cycle_timestamp",
        "destination",
        "source_code",
        "truck_id",
        "loading_unit_id",
        "x",
        "y",
        "z",
    ]
    block_cols = ["x", "y", "z", "penetration_rate", "hardness_class"]
    _require_columns(haulage_cycles_raw, cycle_cols, "haulage_cycles_raw")
    _require_columns(hardness_block_model_raw, block_cols, "hardness_block_model_raw")

    cycles = haulage_cycles_raw[cycle_cols].copy()
    cycles["cycle_timestamp"] = pd.to_datetime(cycles["cycle_timestamp"], errors="coerce")
    cycles = cycles.loc[cycles["destination"].eq("PROCESS_FEED")].dropna(
        subset=["cycle_timestamp", "x", "y", "z"]
    )
    blocks = hardness_block_model_raw[block_cols].dropna(subset=block_cols).copy()
    tree = cKDTree(blocks[["x", "y", "z"]].to_numpy(dtype=float))
    distance, index = tree.query(cycles[["x", "y", "z"]].to_numpy(dtype=float), k=1)
    matched = blocks.iloc[index].reset_index(drop=True)
    cycles = cycles.reset_index(drop=True)
    cycles["hardness_match_distance_m"] = distance
    within_tolerance = cycles["hardness_match_distance_m"].le(
        spatial["max_hardness_match_distance_m"]
    )
    cycles["penetration_rate"] = matched["penetration_rate"].where(within_tolerance)
    cycles["hardness_class"] = matched["hardness_class"].where(within_tolerance, "unmatched")
    cycles["has_hardness_match"] = within_tolerance
    cycles["date"] = cycles["cycle_timestamp"].dt.normalize()
    cycles["source_area"] = cycles["source_code"].map(classify_source_area)
    return cycles


def classify_source_area(source_code: str) -> str:
    """
    Reduce un código normalizado de banco o stock a un área estable de procedencia.

    Parámetros:
    -------------
    source_code : código original de la fuente de mineral.

    Retorna:
    ---------
    str : área reconocida o ``UNCLASSIFIED`` cuando el código no cumple el patrón.
    """
    value = str(source_code).strip().upper()
    match = re.match(r"^(SOURCE_[A-H])", value)
    return match.group(1) if match else "UNCLASSIFIED"


def _robust_hull(points: np.ndarray, trim_quantile: float) -> np.ndarray | None:
    """
    Calcula una envolvente convexa robusta después de recortar extremos espaciales.

    Parámetros:
    -------------
    points : coordenadas bidimensionales candidatas para la envolvente.
    trim_quantile : cuantíl simétrico usado para recortar valores extremos.

    Retorna:
    ---------
    np.ndarray | None : vértices ordenados de la envolvente o ``None`` si no puede estimarse.
    """
    points = np.asarray(points, dtype=float)
    points = points[np.isfinite(points).all(axis=1)]
    if len(points) < 3:
        return None
    if len(points) >= 20:
        x_low, x_high = np.quantile(points[:, 0], [trim_quantile, 1 - trim_quantile])
        y_low, y_high = np.quantile(points[:, 1], [trim_quantile, 1 - trim_quantile])
        trimmed = points[
            (points[:, 0] >= x_low)
            & (points[:, 0] <= x_high)
            & (points[:, 1] >= y_low)
            & (points[:, 1] <= y_high)
        ]
        if len(trimmed) >= 3:
            points = trimmed
    try:
        hull = ConvexHull(points)
    except QhullError:
        return None
    return points[hull.vertices]


def build_training_mine_geometry(
    haulage_cycles_with_hardness: pd.DataFrame,
    spatial: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aprende zonas con historia previa al período evaluado para evitar fuga espacial.

    Parámetros:
    -------------
    haulage_cycles_with_hardness : ciclos enriquecidos con procedencia, dureza y coordenadas.
    spatial : configuración del período de entrenamiento, clustering y envolventes.

    Retorna:
    ---------
    tuple[pd.DataFrame, pd.DataFrame] : componentes espaciales aprendidos y sus vértices.
    """
    training_end = pd.Timestamp(spatial["geometry_training_end"])
    points = haulage_cycles_with_hardness.loc[
        haulage_cycles_with_hardness["date"].le(training_end)
        & haulage_cycles_with_hardness["source_area"].ne("UNCLASSIFIED")
    ].copy()
    grid_m = float(spatial["grid_m"])
    points["x_bin"] = np.rint(points["x"] / grid_m) * grid_m
    points["y_bin"] = np.rint(points["y"] / grid_m) * grid_m

    components: list[dict] = []
    vertices: list[dict] = []
    component_id = 0
    for source_area, area_df in points.groupby("source_area", sort=True):
        bins = area_df.groupby(["x_bin", "y_bin"], as_index=False).size()
        if len(bins) >= spatial["dbscan_min_samples"]:
            bins["component"] = DBSCAN(
                eps=spatial["dbscan_eps_m"],
                min_samples=spatial["dbscan_min_samples"],
            ).fit_predict(bins[["x_bin", "y_bin"]])
        else:
            bins["component"] = 0
        component_map = bins.set_index(["x_bin", "y_bin"])["component"]
        area_df = area_df.copy()
        area_df["component"] = list(zip(area_df["x_bin"], area_df["y_bin"], strict=False))
        area_df["component"] = area_df["component"].map(component_map)
        area_df = area_df.loc[area_df["component"].ge(0)]
        support = area_df["component"].value_counts()
        min_support = max(
            int(spatial["min_cycles_per_component"]),
            int(np.ceil(len(area_df) * spatial["min_component_share"])),
        )
        valid = support.loc[support.ge(min_support)].index.tolist()
        if not valid and not support.empty:
            valid = [support.index[0]]

        for rank, label in enumerate(valid, start=1):
            component_points = area_df.loc[area_df["component"].eq(label)]
            hull = _robust_hull(
                component_points[["x", "y"]].to_numpy(),
                spatial["hull_trim_quantile"],
            )
            if hull is None:
                continue
            component_id += 1
            components.append(
                {
                    "component_id": component_id,
                    "source_area": source_area,
                    "component_rank": rank,
                    "n_training_cycles": len(component_points),
                    "z_low": component_points["z"].quantile(0.05),
                    "z_high": component_points["z"].quantile(0.95),
                }
            )
            vertices.extend(
                {
                    "component_id": component_id,
                    "vertex_order": order,
                    "x": float(x),
                    "y": float(y),
                }
                for order, (x, y) in enumerate(hull, start=1)
            )
    return pd.DataFrame(components), pd.DataFrame(vertices)


def build_daily_spatial_context(
    haulage_cycles_with_hardness: pd.DataFrame,
    mine_zone_components: pd.DataFrame,
    mine_zone_vertices: pd.DataFrame,
) -> pd.DataFrame:
    """
    Asigna zonas aprendidas a cada ciclo y agrega procedencia y dureza por día.

    Parámetros:
    -------------
    haulage_cycles_with_hardness : ciclos enriquecidos que se desea clasificar.
    mine_zone_components : metadatos de los componentes espaciales aprendidos.
    mine_zone_vertices : vértices ordenados de los polígonos de cada componente.

    Retorna:
    ---------
    pd.DataFrame : soporte diario y composiciones porcentuales de zona y dureza.
    """
    cycles = haulage_cycles_with_hardness.copy()
    cycles["mine_zone"] = "UNASSIGNED"
    for component in mine_zone_components.itertuples(index=False):
        mask = cycles["source_area"].eq(component.source_area)
        if not mask.any():
            continue
        polygon = (
            mine_zone_vertices.loc[mine_zone_vertices["component_id"].eq(component.component_id)]
            .sort_values("vertex_order")[["x", "y"]]
            .to_numpy()
        )
        inside = PolygonPath(polygon).contains_points(cycles.loc[mask, ["x", "y"]].to_numpy())
        indices = cycles.loc[mask].index[inside]
        cycles.loc[indices, "mine_zone"] = (
            f"{component.source_area}_ZONE_{int(component.component_rank)}"
        )
    fallback = cycles["mine_zone"].eq("UNASSIGNED") & cycles["source_area"].ne("UNCLASSIFIED")
    cycles.loc[fallback, "mine_zone"] = cycles.loc[fallback, "source_area"] + "_OUTSIDE"

    daily = cycles.groupby("date", as_index=False).agg(
        n_feed_cycles=("mine_zone", "size"),
        penetration_rate_mean=("penetration_rate", "mean"),
        hardness_match_pct=("has_hardness_match", lambda x: 100 * x.mean()),
    )
    zone_shares = (
        pd.crosstab(cycles["date"], cycles["mine_zone"], normalize="index")
        .mul(100)
        .rename(columns=lambda value: f"zone_share__{value.lower()}")
        .reset_index()
    )
    hardness_shares = (
        pd.crosstab(cycles["date"], cycles["hardness_class"], normalize="index")
        .mul(100)
        .rename(columns=lambda value: f"hardness_share__{str(value).lower()}")
        .reset_index()
    )
    return daily.merge(zone_shares, on="date", how="left").merge(
        hardness_shares, on="date", how="left"
    )
