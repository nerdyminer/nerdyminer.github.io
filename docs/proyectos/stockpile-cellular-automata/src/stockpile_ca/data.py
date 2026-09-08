"""Lectura y curación del escenario sintético publicado."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl

PUBLIC_START = dt.datetime(2036, 3, 1, tzinfo=dt.UTC)
MAXIMUM_DAYS = 61
PUBLIC_DATA = Path(__file__).parents[2] / "source" / "public_synthetic_scenario.parquet"


def public_minute_series(days: int = 14, start_day: int = 0) -> pl.DataFrame:
    """Carga una ventana futura, sintética y determinista.

    El artefacto contiene únicamente nombres canónicos, fechas ficticias y las
    irregularidades operacionales necesarias para el ejercicio pedagógico.
    """
    if not 1 <= days <= MAXIMUM_DAYS:
        raise ValueError(f"days debe pertenecer a [1, {MAXIMUM_DAYS}]")
    if start_day < 0 or start_day + days > MAXIMUM_DAYS:
        raise ValueError("start_day y days deben definir una ventana contenida en 61 días")
    if not PUBLIC_DATA.is_file():
        raise FileNotFoundError(
            f"no existe el escenario sintético publicado en {PUBLIC_DATA}"
        )

    start = PUBLIC_START + dt.timedelta(days=start_day)
    end = start + dt.timedelta(days=days)
    return (
        pl.scan_parquet(PUBLIC_DATA)
        .filter(pl.col("timestamp").is_between(start, end, closed="left"))
        .collect()
    )


def curate_minute_series(raw: pl.DataFrame) -> pl.DataFrame:
    """Aplica el contrato tabular sin abandonar expresiones vectorizadas."""
    required = {
        "timestamp",
        "feed_tph",
        "discharge_a_tph",
        "discharge_b_tph",
        "feed_p80_in",
        "measured_height_m",
    }
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"columnas ausentes: {sorted(missing)}")

    return (
        raw.lazy()
        .sort("timestamp")
        .with_columns(
            pl.col("feed_tph").clip(0, 10_000),
            pl.col("discharge_a_tph").clip(0, 10_000),
            pl.col("discharge_b_tph").clip(0, 10_000),
            (pl.col("feed_tph") - pl.col("discharge_a_tph") - pl.col("discharge_b_tph"))
            .truediv(60.0)
            .alias("inventory_delta_t"),
            pl.col("timestamp").dt.date().alias("day"),
        )
        .filter(pl.col("feed_p80_in").is_between(0.05, 30.0))
        .collect()
    )
