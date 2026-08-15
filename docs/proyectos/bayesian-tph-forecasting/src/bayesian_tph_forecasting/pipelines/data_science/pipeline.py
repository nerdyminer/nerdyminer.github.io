"""
Define de forma declarativa la pipeline de ciencia de datos.
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import assemble_model_input, fit_geological_signatures


def create_pipeline(**kwargs) -> Pipeline:
    """
    Construye los nodos de firmas geológicas y ensamblado del contrato modelable.

    Parámetros:
    -------------
    **kwargs : argumentos adicionales reservados por la interfaz de creación de Kedro.

    Retorna:
    ---------
    Pipeline : pipeline localizada de ciencia de datos.
    """
    return pipeline(
        [
            node(
                fit_geological_signatures,
                ["geology_composition_daily", "params:geology_clustering"],
                [
                    "geological_signatures_daily",
                    "geological_clustering_artifact",
                    "clustering_diagnostics",
                ],
                name="fit_training_only_geological_signatures",
                tags=["clustering", "no_leakage"],
            ),
            node(
                assemble_model_input,
                [
                    "plant_target_daily",
                    "plant_context_daily",
                    "geological_signatures_daily",
                    "spatial_context_daily",
                    "params:analysis",
                    "params:spatial",
                    "params:bayesian",
                ],
                ["model_input_daily", "model_input_schema"],
                name="assemble_daily_model_contract",
                tags=["features", "contract"],
            ),
        ],
        namespace="data_science",
        inputs={
            "geology_composition_daily",
            "plant_target_daily",
            "plant_context_daily",
            "spatial_context_daily",
        },
        outputs={
            "geological_signatures_daily",
            "geological_clustering_artifact",
            "clustering_diagnostics",
            "model_input_daily",
            "model_input_schema",
        },
        parameters={
            "params:geology_clustering",
            "params:analysis",
            "params:spatial",
            "params:bayesian",
        },
    )
