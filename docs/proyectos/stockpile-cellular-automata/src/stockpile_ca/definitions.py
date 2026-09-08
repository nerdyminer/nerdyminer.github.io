"""Punto de entrada que Dagster descubre sin contaminar el dominio."""

import dagster as dg
from stockpile_ca.defs.assets import (
    height_reconciliation,
    minute_contract,
    public_minute_curated,
    public_minute_raw,
    stockpile_replay,
)

defs = dg.Definitions(
    assets=[public_minute_raw, public_minute_curated, stockpile_replay],
    asset_checks=[minute_contract, height_reconciliation],
)
