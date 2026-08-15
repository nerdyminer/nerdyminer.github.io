"""Genera desde cero los datos públicos del caso didáctico de forecasting."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]
RAW = ROOT / "data" / "01_raw"
SEED = 20260814


def _states(rng: np.random.Generator, n: int, availability: float) -> np.ndarray:
    """
    Crea una señal sintética de disponibilidad con transiciones suaves.

    Parámetros:
    -------------
    rng : generador seudoaleatorio independiente usado por el caso público.
    n : número de observaciones que se desea producir.
    availability : disponibilidad marginal objetivo entre cero y uno.

    Retorna:
    ---------
    np.ndarray : señal normalizada de disponibilidad con longitud ``n``.
    """
    state = rng.random(n) < availability
    for index in range(1, n):
        if rng.random() < 0.94:
            state[index] = state[index - 1]
    signal = state.astype(float) + rng.normal(0, 0.012, n)
    return np.clip(signal, 0, 1)


def generate_geology(rng: np.random.Generator) -> None:
    """
    Construye composiciones geológicas ficticias sin copiar series históricas.

    Parámetros:
    -------------
    rng : generador seudoaleatorio independiente usado por el caso público.

    Retorna:
    ---------
    None. La función escribe el contrato geológico diario en ``data/01_raw``.
    """
    dates = pd.date_range("2032-01-01", "2035-12-31", freq="D")
    n = len(dates)
    seasonal = 1 + 0.07 * np.sin(np.arange(n) * 2 * np.pi / 181)
    feed = np.clip(rng.normal(43_000, 5_800, n) * seasonal, 18_000, 62_000)
    feed[rng.random(n) < 0.018] = 0
    lithology = rng.dirichlet([2.4, 3.2, 1.7, 2.8, 1.2, 2.0, 1.5], n) * feed[:, None]
    quality = rng.dirichlet([3.1, 4.0, 2.2], n) * feed[:, None]
    frame = pd.DataFrame({"date": dates})
    for index, name in enumerate("alpha bravo charlie delta echo foxtrot golf".split()):
        frame[f"lithology_{name}"] = lithology[:, index].round(3)
    for index, name in enumerate("massive jointed brecciated".split()):
        frame[f"quality_{name}"] = quality[:, index].round(3)
    frame["feed_tonnes"] = feed.round(3)
    frame.to_csv(RAW / "geology_daily.csv", index=False)


def generate_spatial_data(rng: np.random.Generator) -> None:
    """
    Genera un marco cartesiano local ficticio y ciclos independientes de una mina real.

    Parámetros:
    -------------
    rng : generador seudoaleatorio independiente usado por el caso público.

    Retorna:
    ---------
    None. La función escribe el modelo de dureza y los ciclos sintéticos de transporte.
    """
    source_names = [f"SOURCE_{letter}" for letter in "ABCDEFGH"]
    centers = np.array(
        [
            [-2100, -900, -180],
            [-1200, 650, -260],
            [-300, -1200, -340],
            [650, 900, -420],
            [1450, -500, -500],
            [2200, 750, -580],
            [-1650, 1450, -300],
            [1200, 1550, -460],
        ],
        dtype=float,
    )

    block_rows: list[pd.DataFrame] = []
    for source_index, center in enumerate(centers):
        n_blocks = 4_000
        xyz = rng.normal(center, [330, 270, 75], (n_blocks, 3))
        hardness = np.clip(
            31 + source_index * 1.6 + 0.004 * xyz[:, 0] - 0.012 * xyz[:, 2]
            + rng.normal(0, 4.5, n_blocks),
            12,
            62,
        )
        block_rows.append(
            pd.DataFrame(
                {
                    "x": xyz[:, 0].round(3),
                    "y": xyz[:, 1].round(3),
                    "z": xyz[:, 2].round(3),
                    "penetration_rate": hardness.round(4),
                    "hardness_class": pd.cut(
                        hardness,
                        bins=[-np.inf, 27, 36, 45, np.inf],
                        labels=["soft", "medium", "hard", "very_hard"],
                    ).astype(str),
                }
            )
        )
    blocks = pd.concat(block_rows, ignore_index=True)
    blocks.to_parquet(RAW / "hardness_block_model.parquet", index=False)

    days = pd.date_range("2034-01-01", "2035-12-31", freq="D")
    n_cycles_by_day = rng.poisson(82, len(days)) + 28
    n_cycles = int(n_cycles_by_day.sum())
    day_values = np.repeat(days.to_numpy(), n_cycles_by_day)
    seconds = rng.integers(0, 86_400, n_cycles)
    timestamps = pd.to_datetime(day_values) + pd.to_timedelta(seconds, unit="s")
    source_index = rng.choice(len(source_names), n_cycles, p=[0.17, 0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.08])
    xyz = centers[source_index] + rng.normal(0, [240, 210, 55], (n_cycles, 3))
    cycles = pd.DataFrame(
        {
            "cycle_timestamp": timestamps,
            "destination": "PROCESS_FEED",
            "source_code": [f"{source_names[i]}_SECTOR_{rng.integers(1, 7):02d}" for i in source_index],
            "truck_id": [f"HAUL_UNIT_{value:03d}" for value in rng.integers(1, 19, n_cycles)],
            "loading_unit_id": [f"LOAD_UNIT_{value:03d}" for value in rng.integers(1, 9, n_cycles)],
            "x": xyz[:, 0].round(3),
            "y": xyz[:, 1].round(3),
            "z": xyz[:, 2].round(3),
        }
    ).sort_values("cycle_timestamp", ignore_index=True)
    cycles.to_parquet(RAW / "haulage_cycles.parquet", index=False)


def generate_plant(rng: np.random.Generator) -> None:
    """
    Simula señales de un circuito didáctico sin reproducir capacidades reales.

    Parámetros:
    -------------
    rng : generador seudoaleatorio independiente usado por el caso público.

    Retorna:
    ---------
    None. La función escribe las señales horarias ficticias en ``data/01_raw``.
    """
    timestamps = pd.date_range("2034-01-01", "2035-12-31 23:00:00", freq="h")
    n = len(timestamps)
    t = np.arange(n)
    context = 1 + 0.06 * np.sin(2 * np.pi * t / (24 * 73)) + rng.normal(0, 0.045, n)
    feed_a = np.clip(1_180 * context + rng.normal(0, 105, n), 0, 1_650)
    feed_b = np.clip(1_050 * context + rng.normal(0, 115, n), 0, 1_580)
    feed_a[rng.random(n) < 0.025] = 0
    feed_b[rng.random(n) < 0.031] = 0
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "line_a_feed_tph": feed_a,
            "line_b_feed_tph": feed_b,
            "line_a_power_kw": np.clip(2_100 + 3.2 * feed_a + rng.normal(0, 260, n), 80, 8_300),
            "line_b_power_kw": np.clip(2_000 + 3.3 * feed_b + rng.normal(0, 270, n), 80, 8_100),
            "intermediate_stockpile_level_m": np.clip(rng.normal(13.5, 3.2, n), 0, 23),
            "line_a_discharge_sump_pct": np.clip(rng.normal(67, 12, n), 0, 100),
            "line_b_discharge_sump_pct": np.clip(rng.normal(65, 13, n), 0, 100),
            "feed_fines_pct": np.clip(rng.normal(29, 8, n), 2, 68),
        }
    )
    for number, availability in enumerate([0.86, 0.82, 0.79], start=1):
        frame[f"auxiliary_crusher_{number}_state"] = _states(rng, n, availability)
    for line, availability in (("a", 0.89), ("b", 0.87)):
        for number in range(1, 4):
            frame[f"line_{line}_pump_{number}_state"] = _states(rng, n, availability - 0.025 * number)
        for number in range(1, 3):
            frame[f"line_{line}_ball_mill_{number}_state"] = _states(rng, n, availability + 0.035)
    frame.to_parquet(RAW / "plant_signals_hourly.parquet", index=False)


def main() -> None:
    """
    Regenera de forma determinista los cuatro contratos de entrada públicos.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La función materializa los archivos sintéticos en ``data/01_raw``.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    generate_geology(rng)
    generate_spatial_data(rng)
    generate_plant(rng)


if __name__ == "__main__":
    main()
