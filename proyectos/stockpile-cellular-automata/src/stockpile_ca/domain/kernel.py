"""Núcleo didáctico del autómata celular continuo tridimensional."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stockpile_ca.contracts import SimulationSpec
from stockpile_ca.domain.segregation import segregate_sizes

FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class StockpileState:
    """Estado mínimo: llenado y P80 local de cada celda."""

    fill: FloatArray
    p80_in: FloatArray

    @classmethod
    def empty(cls, spec: SimulationSpec) -> StockpileState:
        shape = (spec.grid.n_vertical, spec.grid.n_north, spec.grid.n_east)
        return cls(fill=np.zeros(shape), p80_in=np.zeros(shape))

    @property
    def occupied_fraction(self) -> float:
        return float(self.fill.mean())


def seed_conical_pile(
    state: StockpileState, spec: SimulationSpec, apex_height_m: float, p80_in: float
) -> None:
    """Inicializa un cono discretizado para evitar un arranque físicamente vacío."""
    centre_north = spec.grid.n_north // 2
    centre_east = spec.grid.n_east // 2
    slope = np.tan(np.deg2rad(spec.stockpile.angle_of_repose_deg))
    for north in range(spec.grid.n_north):
        for east in range(spec.grid.n_east):
            radius_m = np.hypot(north - centre_north, east - centre_east) * spec.grid.cell_size_m
            height_cells = max(0.0, (apex_height_m - slope * radius_m) / spec.grid.cell_size_m)
            full = min(int(height_cells), spec.grid.n_vertical)
            state.fill[:full, north, east] = 1.0
            state.p80_in[:full, north, east] = p80_in
            if full < spec.grid.n_vertical and height_cells - full > 0:
                state.fill[full, north, east] = height_cells - full
                state.p80_in[full, north, east] = p80_in


def column_height(state: StockpileState, north: int, east: int) -> float:
    """Altura de una columna en unidades de celda, incluidas celdas parciales."""
    return float(state.fill[:, north, east].sum())


def _mix(existing_size: float, existing_volume: float, new_size: float, new_volume: float) -> float:
    total = existing_volume + new_volume
    return (
        new_size
        if total <= 0
        else (existing_size * existing_volume + new_size * new_volume) / total
    )


def add_to_top(
    state: StockpileState,
    north: int,
    east: int,
    volume_cells: float,
    p80_in: float,
) -> None:
    """Añade volumen y mezcla propiedades en la superficie de una columna."""
    remaining = volume_cells
    for level in range(state.fill.shape[0]):
        capacity = 1.0 - state.fill[level, north, east]
        if capacity <= 0:
            continue
        moved = min(capacity, remaining)
        old_fill = state.fill[level, north, east]
        state.p80_in[level, north, east] = _mix(
            state.p80_in[level, north, east], old_fill, p80_in, moved
        )
        state.fill[level, north, east] += moved
        remaining -= moved
        if remaining <= 1e-12:
            return
    raise OverflowError("la alimentacion supera el techo de la grilla")


def remove_from_bottom(
    state: StockpileState,
    north: int,
    east: int,
    volume_cells: float,
) -> tuple[float, float]:
    """Extrae desde el punto de descarga y migra el vacío hacia arriba."""
    remaining = volume_cells
    removed = 0.0
    size_moment = 0.0
    for level in range(state.fill.shape[0]):
        available = state.fill[level, north, east]
        if available <= 0:
            continue
        moved = min(available, remaining)
        removed += moved
        size_moment += moved * state.p80_in[level, north, east]
        state.fill[level, north, east] -= moved
        remaining -= moved
        if remaining <= 1e-12:
            break

    # Compactar la columna es la versión determinista de migración vertical. El
    # modelo completo elige vecinos superiores con una probabilidad espacial.
    occupied = state.fill[:, north, east] > 0
    fills = state.fill[occupied, north, east].copy()
    sizes = state.p80_in[occupied, north, east].copy()
    state.fill[:, north, east] = 0.0
    state.p80_in[:, north, east] = 0.0
    state.fill[: len(fills), north, east] = fills
    state.p80_in[: len(sizes), north, east] = sizes
    return removed, size_moment / removed if removed > 0 else float("nan")


def remove_from_top(
    state: StockpileState,
    north: int,
    east: int,
    volume_cells: float,
) -> tuple[float, float]:
    """Retira material superficial sin activar la migración de una descarga basal."""
    remaining = volume_cells
    removed = 0.0
    size_moment = 0.0
    for level in range(state.fill.shape[0] - 1, -1, -1):
        available = state.fill[level, north, east]
        if available <= 0:
            continue
        moved = min(available, remaining)
        removed += moved
        size_moment += moved * state.p80_in[level, north, east]
        state.fill[level, north, east] -= moved
        if state.fill[level, north, east] <= 1e-12:
            state.fill[level, north, east] = 0.0
            state.p80_in[level, north, east] = 0.0
        remaining -= moved
        if remaining <= 1e-12:
            break
    return removed, size_moment / removed if removed > 0 else float("nan")


def equilibrate_surface(
    state: StockpileState, spec: SimulationSpec, rng: np.random.Generator
) -> None:
    """Relaja pendientes que exceden el ángulo de reposo usando Moore asíncrono."""
    threshold_cardinal = np.tan(np.deg2rad(spec.stockpile.angle_of_repose_deg))
    offsets = np.array([[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]])
    points = [
        (north, east)
        for north in range(1, spec.grid.n_north - 1)
        for east in range(1, spec.grid.n_east - 1)
    ]
    rng.shuffle(points)

    for north, east in points:
        source_height = column_height(state, north, east)
        if source_height <= 0:
            continue
        rng.shuffle(offsets)
        for dn, de in offsets:
            target_north, target_east = north + int(dn), east + int(de)
            target_height = column_height(state, target_north, target_east)
            threshold = threshold_cardinal * (np.sqrt(2.0) if dn and de else 1.0)
            excess = source_height - target_height - threshold
            if excess <= 0:
                continue
            flow = min(excess / 2.0, 0.45)
            level = max(0, int(np.ceil(source_height)) - 1)
            mixture_size = state.p80_in[level, north, east]
            fine, coarse = segregate_sizes(
                mixture_size,
                spec.segregation.fine_limit_in,
                spec.segregation.coarse_limit_in,
                spec.segregation.surface_strength,
            )
            moved, _ = remove_from_top(state, north, east, flow)
            if moved > 0:
                add_to_top(state, target_north, target_east, moved, coarse)
                # El remanente fino se expresa al mezclar la superficie fuente.
                new_level = max(0, int(np.ceil(column_height(state, north, east))) - 1)
                if state.fill[new_level, north, east] > 0:
                    state.p80_in[new_level, north, east] = fine
            break


def run_step(
    state: StockpileState,
    spec: SimulationSpec,
    feed_volume_cells: float,
    feed_p80_in: float,
    discharge_volume_cells: tuple[float, ...],
    rng: np.random.Generator,
) -> tuple[float, ...]:
    """Ejecuta alimentación, descarga, migración y flujo superficial en ese orden."""
    centre_north = spec.grid.n_north // 2
    centre_east = spec.grid.n_east // 2
    # Una correa no descarga sobre un punto matemático. Repartir el paquete en
    # una huella pequeña evita una aguja numérica y deja que una leve asimetría
    # operacional sobreviva sin revelar geometría de una instalación real.
    feed_footprint = (
        (0, 0),
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    )
    base_weights = np.array(
        [0.20, 0.12, 0.12, 0.12, 0.12, 0.08, 0.08, 0.08, 0.08],
        dtype=np.float64,
    )
    weights = base_weights * rng.uniform(0.86, 1.14, len(feed_footprint))
    weights /= weights.sum()
    for (dn, de), weight in zip(feed_footprint, weights, strict=True):
        add_to_top(
            state,
            centre_north + dn,
            centre_east + de,
            feed_volume_cells * float(weight),
            feed_p80_in,
        )
    discharged_sizes: list[float] = []
    for feeder, volume in zip(spec.feeders, discharge_volume_cells, strict=True):
        _, size = remove_from_bottom(state, feeder.north, feeder.east, volume)
        discharged_sizes.append(size)
    for _ in range(2):
        equilibrate_surface(state, spec, rng)
    return tuple(discharged_sizes)
