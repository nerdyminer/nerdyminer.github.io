import dagster as dg
from stockpile_ca.definitions import defs


def test_public_asset_graph_has_expected_lineage_and_checks() -> None:
    graph = defs.resolve_asset_graph()
    assets = {key.to_user_string() for key in graph.get_all_asset_keys()}
    checks = {(key.asset_key.to_user_string(), key.name) for key in graph.asset_check_keys}

    assert assets == {"public_minute_raw", "public_minute_curated", "stockpile_replay"}
    assert {
        parent.key.to_user_string()
        for parent in graph.get_parents(graph.get(dg.AssetKey("stockpile_replay")))
    } == {"public_minute_curated"}
    assert checks == {
        ("public_minute_curated", "minute_contract"),
        ("stockpile_replay", "height_reconciliation"),
    }
