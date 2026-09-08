import datetime as dt

import polars as pl

from stockpile_ca.data import curate_minute_series, public_minute_series


def test_public_data_are_future_deterministic_and_complete() -> None:
    first = curate_minute_series(public_minute_series(days=2))
    second = curate_minute_series(public_minute_series(days=2))
    assert first.equals(second)
    assert first.null_count().row(0) == (0,) * first.width
    assert first["timestamp"].min().year >= 2036
    assert first["timestamp"].max() - first["timestamp"].min() == dt.timedelta(minutes=2879)


def test_public_scenario_contains_a_multiday_shutdown_and_starvation() -> None:
    data = curate_minute_series(public_minute_series(days=61))
    shutdown = data.filter(pl.col("feed_tph") < 1.0)

    assert shutdown.height >= 3 * 24 * 60
    assert data.filter(pl.col("primary_running") < 0.5).height >= 3 * 24 * 60
    assert data["measured_height_m"].min() < 1.0


def test_public_height_is_driven_by_drawdown_not_a_small_periodic_wave() -> None:
    data = public_minute_series(days=61)
    height_range = data["measured_height_m"].max() - data["measured_height_m"].min()

    assert height_range > 20.0
    assert data["measured_height_m"].min() < 1.0


def test_public_transform_uses_requested_height_and_psd_factors() -> None:
    data = public_minute_series(days=61)

    assert 30.0 < data["measured_height_m"].max() < 32.0
    assert data["feed_p80_in"].median() > 0.0
    assert data["timestamp"].min() == dt.datetime(2036, 3, 1, tzinfo=dt.UTC)
