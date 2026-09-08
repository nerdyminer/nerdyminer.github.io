"""Función de segregación inspirada en la formulación de Ye et al. (2022)."""

from __future__ import annotations

import math


def fine_proportion(p80_in: float, fine_limit_in: float, coarse_limit_in: float) -> float:
    """Normaliza un tamaño característico entre los extremos segregables."""
    if not 0 < fine_limit_in < coarse_limit_in:
        raise ValueError("los limites de segregacion deben ser positivos y ordenados")
    return min(1.0, max(0.0, (coarse_limit_in - p80_in) / (coarse_limit_in - fine_limit_in)))


def segregate_sizes(
    mixture_p80_in: float,
    fine_limit_in: float,
    coarse_limit_in: float,
    strength: float,
) -> tuple[float, float]:
    """Devuelve tamaños fino y grueso conservando el tamaño medio de la mezcla.

    La intensidad cero deja ambos productos iguales a la mezcla. Una intensidad
    mayor separa los productos hacia los límites, pero la media ponderada por la
    fracción fina permanece idéntica: la segregación redistribuye, no conmuta.
    """
    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength debe pertenecer a [0, 1]")
    phi = fine_proportion(mixture_p80_in, fine_limit_in, coarse_limit_in)
    if phi in (0.0, 1.0):
        return mixture_p80_in, mixture_p80_in
    maximum_spread = min(
        (mixture_p80_in - fine_limit_in) / (1.0 - phi),
        (coarse_limit_in - mixture_p80_in) / phi,
    )
    fine = mixture_p80_in - strength * (1.0 - phi) * maximum_spread
    coarse = mixture_p80_in + strength * phi * maximum_spread
    if not math.isclose(phi * fine + (1.0 - phi) * coarse, mixture_p80_in, rel_tol=1e-12):
        raise RuntimeError("la funcion de segregacion violo la conservacion del tamano medio")
    return fine, coarse
