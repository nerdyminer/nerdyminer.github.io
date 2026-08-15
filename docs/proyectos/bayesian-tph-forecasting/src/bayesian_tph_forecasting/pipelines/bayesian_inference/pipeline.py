"""
Define de forma declarativa la pipeline de inferencia Bayesiana.
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import fit_final_model, run_rolling_backtest


def create_pipeline(**kwargs) -> Pipeline:
    """
    Construye los nodos de backtesting móvil y ajuste final del modelo jerárquico.

    Parámetros:
    -------------
    **kwargs : argumentos adicionales reservados por la interfaz de creación de Kedro.

    Retorna:
    ---------
    Pipeline : pipeline localizada de inferencia Bayesiana.
    """
    return pipeline(
        [
            node(
                run_rolling_backtest,
                [
                    "model_input_daily",
                    "params:bayesian",
                    "params:features",
                    "params:backtest",
                ],
                ["backtest_predictions", "backtest_fold_metrics", "backtest_summary"],
                name="run_rolling_twelve_month_backtest",
                tags=["backtest", "rolling"],
            ),
            node(
                fit_final_model,
                ["model_input_daily", "params:bayesian", "params:features"],
                ["final_inference_data", "posterior_parameter_summary"],
                name="fit_final_identifiable_hierarchical_model",
                tags=["bayesian", "final_model"],
            ),
        ],
        namespace="bayesian_inference",
        inputs={"model_input_daily"},
        outputs={
            "backtest_predictions",
            "backtest_fold_metrics",
            "backtest_summary",
            "final_inference_data",
            "posterior_parameter_summary",
        },
        parameters={"params:bayesian", "params:features", "params:backtest"},
    )
