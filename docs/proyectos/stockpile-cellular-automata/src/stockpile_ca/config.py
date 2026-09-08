"""Carga TOML y valida antes de construir cualquier arreglo numérico."""

from __future__ import annotations

import tomllib
from pathlib import Path

from stockpile_ca.contracts import SimulationSpec


def load_spec(path: Path | None = None) -> SimulationSpec:
    """Carga la configuración pública y devuelve un contrato inmutable."""
    source = path or Path(__file__).parents[2] / "conf" / "public.toml"
    with source.open("rb") as stream:
        payload = tomllib.load(stream)
    # TOML representa los arreglos de tablas como listas mutables. El contrato
    # público exige una tupla: normalizamos la representación, no los valores.
    payload["feeders"] = tuple(payload.get("feeders", ()))
    return SimulationSpec.model_validate(payload, strict=True)
