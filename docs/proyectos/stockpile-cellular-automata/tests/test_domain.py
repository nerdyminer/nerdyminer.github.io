import math

import numpy as np

from stockpile_ca.config import load_spec
from stockpile_ca.domain.kernel import (
    StockpileState,
    add_to_top,
    remove_from_bottom,
    remove_from_top,
)
from stockpile_ca.domain.segregation import fine_proportion, segregate_sizes


def test_segregation_conserves_the_characteristic_size() -> None:
    mixture = 4.5
    phi = fine_proportion(mixture, 0.25, 10.0)
    fine, coarse = segregate_sizes(mixture, 0.25, 10.0, 0.68)
    assert fine < mixture < coarse
    assert math.isclose(phi * fine + (1 - phi) * coarse, mixture)


def test_feed_and_discharge_conserve_volume() -> None:
    spec = load_spec()
    state = StockpileState.empty(spec)
    add_to_top(state, spec.grid.n_north // 2, spec.grid.n_east // 2, 2.4, 4.2)
    before = state.fill.sum()
    removed, size = remove_from_bottom(state, spec.grid.n_north // 2, spec.grid.n_east // 2, 0.7)
    assert np.isclose(before - state.fill.sum(), removed)
    assert np.isclose(removed, 0.7)
    assert np.isclose(size, 4.2)


def test_surface_flow_removes_the_upper_material_first() -> None:
    spec = load_spec()
    state = StockpileState.empty(spec)
    north = spec.grid.n_north // 2
    east = spec.grid.n_east // 2
    add_to_top(state, north, east, 1.0, 2.0)
    add_to_top(state, north, east, 1.0, 8.0)

    removed, size = remove_from_top(state, north, east, 0.4)

    assert np.isclose(removed, 0.4)
    assert np.isclose(size, 8.0)
    assert np.isclose(state.fill[0, north, east], 1.0)
    assert np.isclose(state.fill[1, north, east], 0.6)
