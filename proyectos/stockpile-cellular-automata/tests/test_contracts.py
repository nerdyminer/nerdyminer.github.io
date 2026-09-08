from pathlib import Path

import pytest
from pydantic import ValidationError

from stockpile_ca.config import load_spec
from stockpile_ca.contracts import GridSpec


def test_public_configuration_is_self_consistent() -> None:
    spec = load_spec(Path(__file__).parents[1] / "conf" / "public.toml")
    assert spec.grid.n_east % 2 == 1
    assert spec.grid.n_north % 2 == 1
    assert {feeder.line for feeder in spec.feeders} == {"A", "B"}


def test_grid_rejects_an_ambiguous_centre() -> None:
    with pytest.raises(ValidationError):
        GridSpec(n_east=40, n_north=41, n_vertical=18, cell_size_m=2.2)
