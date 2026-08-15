"""
Define de forma declarativa la pipeline de ingeniería de datos.
"""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    build_daily_plant_tables,
    build_daily_spatial_context,
    build_geology_composition,
    build_training_mine_geometry,
    clean_plant_signals,
    enrich_haulage_with_hardness,
)


def create_pipeline(**kwargs) -> Pipeline:
    """
    Construye los nodos de limpieza, agregación diaria y contexto espacial de la mina.

    Parámetros:
    -------------
    **kwargs : argumentos adicionales reservados por la interfaz de creación de Kedro.

    Retorna:
    ---------
    Pipeline : pipeline localizada de ingeniería de datos.
    """
    return pipeline(
        [
            node(
                clean_plant_signals,
                "plant_signals_hourly_raw",
                "plant_signals_hourly_clean",
                name="clean_plant_signals",
                tags=["quality", "plant"],
            ),
            node(
                build_daily_plant_tables,
                ["plant_signals_hourly_clean", "params:plant"],
                ["plant_target_daily", "plant_context_daily"],
                name="aggregate_daily_plant_context",
                tags=["plant", "daily"],
            ),
            node(
                build_geology_composition,
                "geology_daily_raw",
                "geology_composition_daily",
                name="close_geological_compositions",
                tags=["geology", "quality"],
            ),
            node(
                enrich_haulage_with_hardness,
                ["haulage_cycles_raw", "hardness_block_model_raw", "params:spatial"],
                "haulage_cycles_with_hardness",
                name="match_haulage_cycles_to_hardness",
                tags=["haulage", "spatial"],
            ),
            node(
                build_training_mine_geometry,
                ["haulage_cycles_with_hardness", "params:spatial"],
                ["mine_zone_components", "mine_zone_vertices"],
                name="learn_training_only_mine_geometry",
                tags=["spatial", "no_leakage"],
            ),
            node(
                build_daily_spatial_context,
                [
                    "haulage_cycles_with_hardness",
                    "mine_zone_components",
                    "mine_zone_vertices",
                ],
                "spatial_context_daily",
                name="aggregate_daily_spatial_context",
                tags=["spatial", "daily"],
            ),
        ],
        namespace="data_engineering",
        inputs={
            "plant_signals_hourly_raw",
            "geology_daily_raw",
            "haulage_cycles_raw",
            "hardness_block_model_raw",
        },
        outputs={
            "plant_signals_hourly_clean",
            "haulage_cycles_with_hardness",
            "mine_zone_components",
            "mine_zone_vertices",
            "plant_target_daily",
            "plant_context_daily",
            "geology_composition_daily",
            "spatial_context_daily",
        },
        parameters={"params:plant", "params:spatial"},
    )
