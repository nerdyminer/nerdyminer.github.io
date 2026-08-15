"""
Registra el DAG global y las pipelines que pueden ejecutarse de manera independiente.
"""

from kedro.pipeline import Pipeline

from bayesian_tph_forecasting.pipelines import (
    bayesian_inference,
    data_engineering,
    data_science,
    reporting,
)


def register_pipelines() -> dict[str, Pipeline]:
    """
    Construye las pipelines locales y compone el flujo global según sus dependencias de datos.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    dict[str, Pipeline] : pipelines registradas por nombre, incluido el flujo predeterminado.
    """
    de_pipeline = data_engineering.create_pipeline()
    ds_pipeline = data_science.create_pipeline()
    bi_pipeline = bayesian_inference.create_pipeline()
    reporting_pipeline = reporting.create_pipeline()
    global_pipeline = de_pipeline + ds_pipeline + bi_pipeline + reporting_pipeline

    return {
        "__default__": global_pipeline,
        "global": global_pipeline,
        "data_engineering": de_pipeline,
        "data_science": ds_pipeline,
        "bayesian_inference": bi_pipeline,
        "reporting": reporting_pipeline,
    }
