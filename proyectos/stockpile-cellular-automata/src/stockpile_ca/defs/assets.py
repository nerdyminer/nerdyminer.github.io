"""Activos declarativos: Dagster orquesta, el dominio conserva la ciencia."""

from __future__ import annotations

import numpy as np
import polars as pl

import dagster as dg
from stockpile_ca.config import load_spec
from stockpile_ca.data import curate_minute_series, public_minute_series
from stockpile_ca.domain.kernel import StockpileState, run_step, seed_conical_pile
from stockpile_ca.domain.reconciliation import agreement


@dg.asset(group_name="ingestion", kinds={"python", "polars"})
def public_minute_raw() -> pl.DataFrame:
    """Ventana sintética determinista, con calendario y equipos ficticios."""
    return public_minute_series(days=14, start_day=30)


@dg.asset(group_name="engineering", kinds={"python", "polars"})
def public_minute_curated(public_minute_raw: pl.DataFrame) -> pl.DataFrame:
    """Contrato tabular minuto a minuto, expresado con Polars."""
    return curate_minute_series(public_minute_raw)


@dg.asset(group_name="simulation", kinds={"python", "numpy"})
def stockpile_replay(public_minute_curated: pl.DataFrame) -> pl.DataFrame:
    """Reproduce una ventana reducida y publica series de reconciliación."""
    spec = load_spec()
    state = StockpileState.empty(spec)
    seed_conical_pile(state, spec, apex_height_m=20.0, p80_in=4.725)
    rng = np.random.default_rng(202603)
    rows: list[dict[str, object]] = []

    # Para mantener rápida la demostración CLI, un minuto de este activo resume
    # un bloque de quince minutos del contrato curado.
    sampled = public_minute_curated.group_by_dynamic(
        "timestamp", every="15m", period="15m", closed="left"
    ).agg(
        pl.col("feed_tph").mean(),
        pl.col("discharge_a_tph").mean(),
        pl.col("discharge_b_tph").mean(),
        pl.col("feed_p80_in").mean(),
        pl.col("measured_height_m").mean(),
    )

    cell_volume = spec.grid.cell_size_m**3
    tonnes_per_cell = cell_volume * spec.stockpile.bulk_density_t_m3
    # Una interacción del núcleo representa un paquete de eventos locales, no
    # los millones de partículas del intervalo. La escala conserva el balance
    # entrada-salida y mantiene el ejemplo rápido para una ejecución pedagógica.
    # La geometría pública redujo la arista de celda junto con la altura. Como
    # el número de celdas por tonelada crece con 1 / cell_size³, la escala del
    # replay debe compensar ese cambio de volumen discretizado. Esto no altera
    # los caudales publicados: sólo fija cuántos eventos locales resume un paso.
    interaction_scale = 0.01
    for row in sampled.iter_rows(named=True):
        feed_cells = float(row["feed_tph"]) * 0.25 / tonnes_per_cell * interaction_scale
        a_cells = float(row["discharge_a_tph"]) * 0.25 / tonnes_per_cell / 3.0 * interaction_scale
        b_cells = float(row["discharge_b_tph"]) * 0.25 / tonnes_per_cell / 3.0 * interaction_scale
        sizes = run_step(
            state,
            spec,
            feed_volume_cells=feed_cells,
            feed_p80_in=float(row["feed_p80_in"]),
            discharge_volume_cells=(a_cells, a_cells, a_cells, b_cells, b_cells, b_cells),
            rng=rng,
        )
        heights = state.fill.sum(axis=0) * spec.grid.cell_size_m
        # El sensor público representa una huella sobre el corredor de
        # extracción, no el máximo absoluto de toda la pila. Así responde a los
        # conos invertidos mientras una corona aislada todavía puede permanecer.
        draw_heights = np.array(
            [heights[feeder.north, feeder.east] for feeder in spec.feeders],
            dtype=np.float64,
        )
        footprint_height = float(np.median(draw_heights) + 8.0)
        rows.append(
            {
                "timestamp": row["timestamp"],
                "simulated_height_m": footprint_height,
                "measured_height_m": float(row["measured_height_m"]),
                "simulated_line_a_p80_in": float(np.nanmean(sizes[:3])),
                "simulated_line_b_p80_in": float(np.nanmean(sizes[3:])),
            }
        )
    return pl.DataFrame(rows)


@dg.asset_check(asset=public_minute_curated, blocking=True)
def minute_contract(public_minute_curated: pl.DataFrame) -> dg.AssetCheckResult:
    """Detiene el DAG si rangos, orden o nulidad dejan de ser publicables."""
    checks = [
        public_minute_curated["timestamp"].is_sorted(),
        public_minute_curated.null_count().row(0) == (0,) * public_minute_curated.width,
        public_minute_curated["feed_p80_in"].is_between(0.05, 30.0).all(),
    ]
    return dg.AssetCheckResult(passed=all(checks), metadata={"rows": public_minute_curated.height})


@dg.asset_check(asset=stockpile_replay)
def height_reconciliation(stockpile_replay: pl.DataFrame) -> dg.AssetCheckResult:
    """Publica métricas sin convertir un mal ajuste en un fallo de software."""
    metrics = agreement(
        stockpile_replay["simulated_height_m"].to_numpy(),
        stockpile_replay["measured_height_m"].to_numpy(),
    )
    return dg.AssetCheckResult(
        passed=bool(np.isfinite(metrics.rmse)),
        metadata={"bias_m": metrics.bias, "mae_m": metrics.mae, "rmse_m": metrics.rmse},
    )
