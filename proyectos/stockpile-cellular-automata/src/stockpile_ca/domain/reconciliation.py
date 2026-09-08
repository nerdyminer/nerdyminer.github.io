"""Métricas que mantienen separada la validación de la calibración."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Agreement:
    bias: float
    mae: float
    rmse: float
    n: int


def agreement(simulated: NDArray[np.float64], measured: NDArray[np.float64]) -> Agreement:
    """Calcula errores sólo donde ambas series son finitas."""
    valid = np.isfinite(simulated) & np.isfinite(measured)
    residual = simulated[valid] - measured[valid]
    if residual.size == 0:
        raise ValueError("no existen pares validos para reconciliar")
    return Agreement(
        bias=float(residual.mean()),
        mae=float(np.abs(residual).mean()),
        rmse=float(np.sqrt(np.square(residual).mean())),
        n=int(residual.size),
    )
