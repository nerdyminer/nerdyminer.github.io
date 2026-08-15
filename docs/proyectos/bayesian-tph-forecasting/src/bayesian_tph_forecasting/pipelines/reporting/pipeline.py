"""
Define de forma declarativa la pipeline que materializa los productos finales.
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    build_bridge_app,
    build_bridge_summary,
    build_model_card,
    plot_bridge_chart,
)


def create_pipeline(**kwargs) -> Pipeline:
    """
    Construye los nodos del bridge, la aplicación interactiva y la ficha del modelo.

    Parámetros:
    -------------
    **kwargs : argumentos adicionales reservados por la interfaz de creación de Kedro.

    Retorna:
    ---------
    Pipeline : pipeline localizada de reporting.
    """
    return pipeline(
        [
            node(
                build_bridge_summary,
                ["backtest_predictions", "params:reporting"],
                "bridge_summary",
                name="build_monthly_and_total_bridges",
                tags=["bridge", "reporting"],
            ),
            node(
                plot_bridge_chart,
                ["bridge_summary", "params:reporting"],
                "bridge_chart",
                name="render_static_bridge_chart",
                tags=["bridge", "figure"],
            ),
            node(
                build_bridge_app,
                ["bridge_summary", "backtest_summary"],
                "bridge_app_html",
                name="build_interactive_bridge_application",
                tags=["bridge", "web_app"],
            ),
            node(
                build_model_card,
                ["backtest_summary", "model_input_schema", "params:reporting"],
                "model_card",
                name="materialize_model_card",
                tags=["governance", "reporting"],
            ),
        ],
        namespace="reporting",
        inputs={"backtest_predictions", "backtest_summary", "model_input_schema"},
        outputs={"bridge_summary", "bridge_chart", "bridge_app_html", "model_card"},
        parameters={"params:reporting"},
    )
