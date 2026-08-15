"""
Verifica los contratos públicos de identificadores, rendimiento y coordenadas de los extractos.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bayesian_tph_forecasting.pipelines.data_engineering.nodes import (
    classify_source_area,
)

PROJECT_ROOT = Path(__file__).parents[1]
RAW = PROJECT_ROOT / "data" / "01_raw"


def test_public_identifiers_follow_generic_contract() -> None:
    """
    Comprueba que los identificadores publicados respeten el contrato genérico documentado.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La prueba falla si un identificador o destino viola el contrato.
    """
    haulage = pd.read_parquet(RAW / "haulage_cycles.parquet")
    assert haulage["destination"].eq("PROCESS_FEED").all()
    assert haulage["truck_id"].str.fullmatch(r"HAUL_UNIT_\d{3}").all()
    assert haulage["loading_unit_id"].str.fullmatch(r"LOAD_UNIT_\d{3}").all()
    assert haulage["source_code"].map(classify_source_area).ne("UNCLASSIFIED").all()


def test_stable_public_line_means_are_in_documented_range() -> None:
    """
    Comprueba que el rendimiento estable medio de cada línea permanezca en el rango publicado.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La prueba falla si la media estable queda fuera del intervalo documentado.
    """
    signals = pd.read_parquet(RAW / "plant_signals_hourly.parquet")
    for line in ("a", "b"):
        stable = signals.loc[
            signals[f"line_{line}_feed_tph"].ge(700) & signals[f"line_{line}_power_kw"].ge(3_500),
            f"line_{line}_feed_tph",
        ]
        assert 1_000 <= stable.mean() <= 1_300


def test_public_spatial_frame_is_self_consistent() -> None:
    """
    Comprueba completitud y coherencia del marco cartesiano local y la dureza.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La prueba falla si existen nulos o coordenadas fuera del marco esperado.
    """
    haulage = pd.read_parquet(RAW / "haulage_cycles.parquet")
    hardness = pd.read_parquet(RAW / "hardness_block_model.parquet")
    assert haulage[["x", "y", "z"]].notna().all().all()
    assert hardness[["x", "y", "z", "penetration_rate", "hardness_class"]].notna().all().all()
    assert haulage["x"].between(-4_000, 4_000).all()
    assert haulage["y"].between(-3_000, 3_000).all()


def test_public_data_are_obviously_fictional() -> None:
    """
    Impide publicar accidentalmente fechas históricas o coordenadas con apariencia UTM.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La prueba falla si reaparece una huella temporal o espacial realista.
    """
    haulage = pd.read_parquet(RAW / "haulage_cycles.parquet")
    signals = pd.read_parquet(RAW / "plant_signals_hourly.parquet")
    assert pd.to_datetime(haulage["cycle_timestamp"]).dt.year.min() >= 2034
    assert pd.to_datetime(signals["timestamp"]).dt.year.min() >= 2034
    assert haulage[["x", "y"]].abs().to_numpy().max() < 10_000
