"""
Verifica las identidades contables de los productos de reporting.
"""

from __future__ import annotations

import pandas as pd

from bayesian_tph_forecasting.pipelines.reporting.nodes import build_bridge_summary


def test_bridge_closes_model_to_observed_identity() -> None:
    """
    Comprueba que el modelo más el residuo operacional cierre exactamente al valor observado.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La prueba falla cuando el bridge no respeta su identidad contable.
    """
    predictions = pd.DataFrame(
        {
            "date": pd.to_datetime(["2035-01-01"]),
            "base_component": [100.0],
            "contrib_geology": [2.0],
            "contrib_source": [-1.0],
            "contrib_hardness_mix": [0.5],
            "contrib__penetration_rate_mean": [0.5],
            "contrib__feed_fines_pct_mean": [1.0],
            "contrib__feed_fines_pct_centered_sq": [0.0],
            "contrib__upstream_available_pct": [1.0],
            "contrib__discharge_sumps_in_range_pct": [1.0],
            "contrib__auxiliary_crushing_available_pct": [1.0],
            "contrib__secondary_grinding_available_pct": [1.0],
            "y_pred_mean": [108.0],
            "residual_actual_minus_model": [-3.0],
            "y_true": [105.0],
        }
    )
    bridge = build_bridge_summary(predictions, reporting={})
    total = bridge.loc[bridge["period"].eq("TOTAL")].set_index("column")["value_tph"]
    assert total["y_pred_mean"] + total["residual_actual_minus_model"] == total["y_true"]
