"""Contratos estrictos e inmutables que protegen la frontera del dominio."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImmutableContract(BaseModel):
    """Base inmutable: rechaza campos desconocidos y coerciones ambiguas."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class GridSpec(ImmutableContract):
    """Resolución cartesiana de la retícula tridimensional."""

    n_east: int = Field(ge=9, le=301)
    n_north: int = Field(ge=9, le=301)
    n_vertical: int = Field(ge=4, le=200)
    cell_size_m: float = Field(gt=0.05, le=20.0)

    @model_validator(mode="after")
    def require_odd_horizontal_axes(self) -> Self:
        """Una celda central única simplifica alimentación y cortes ortogonales."""
        if self.n_east % 2 == 0 or self.n_north % 2 == 0:
            raise ValueError("los ejes horizontales deben tener un numero impar de celdas")
        return self


class StockpileSpec(ImmutableContract):
    """Parámetros geométricos que tienen interpretación física."""

    angle_of_repose_deg: float = Field(gt=15.0, lt=55.0)
    bulk_density_t_m3: float = Field(gt=0.5, lt=4.0)
    design_height_m: float = Field(gt=1.0)


class SegregationSpec(ImmutableContract):
    """Extremos y magnitud adimensional de los mecanismos de segregación."""

    fine_limit_in: float = Field(gt=0.0)
    coarse_limit_in: float = Field(gt=0.0)
    surface_strength: float = Field(ge=0.0, le=1.0)
    trajectory_strength: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def limits_are_ordered(self) -> Self:
        if self.fine_limit_in >= self.coarse_limit_in:
            raise ValueError("fine_limit_in debe ser menor que coarse_limit_in")
        return self


class FeederSpec(ImmutableContract):
    """Punto de extracción expresado en índices de la grilla pública."""

    name: str = Field(pattern=r"^[AB]-[1-3]$")
    line: Literal["A", "B"]
    east: int = Field(ge=0)
    north: int = Field(ge=0)


class ConveyorSpec(ImmutableContract):
    """Orientación pública de la correa de alimentación."""

    label: str = Field(min_length=1)
    bearing_deg: float = Field(ge=0.0, lt=360.0)


class SimulationSpec(ImmutableContract):
    """Contrato agregado consumido por el núcleo y por los activos."""

    grid: GridSpec
    stockpile: StockpileSpec
    segregation: SegregationSpec
    conveyor: ConveyorSpec | None = None
    feeders: tuple[FeederSpec, ...]

    @model_validator(mode="after")
    def geometry_is_self_consistent(self) -> Self:
        if len(self.feeders) != 6:
            raise ValueError("la demostracion publica requiere seis alimentadores")
        for feeder in self.feeders:
            if feeder.east >= self.grid.n_east or feeder.north >= self.grid.n_north:
                raise ValueError(f"{feeder.name} queda fuera de la grilla")
        available_height = self.grid.n_vertical * self.grid.cell_size_m
        if self.stockpile.design_height_m >= available_height:
            raise ValueError("la altura de diseno debe dejar al menos una celda vertical libre")
        return self


class MinuteInput(ImmutableContract):
    """Entrada de un minuto después de las transformaciones de Polars."""

    feed_tph: float = Field(ge=0.0, le=10_000.0)
    discharge_a_tph: float = Field(ge=0.0, le=10_000.0)
    discharge_b_tph: float = Field(ge=0.0, le=10_000.0)
    feed_p80_in: float = Field(gt=0.0, le=30.0)
