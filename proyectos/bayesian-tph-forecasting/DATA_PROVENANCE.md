# Procedencia y límites de los datos públicos

Los cuatro conjuntos de entrada de este proyecto se generan desde cero mediante
[`scripts/generate_public_synthetic_data.py`](scripts/generate_public_synthetic_data.py).
La semilla fija permite reproducir el ejercicio, pero no reconstruir información
industrial externa porque el generador no consume archivos, modelos ni parámetros
de una operación real.

Las salvaguardas deliberadas son:

- calendario situado en los años 2032–2035;
- coordenadas cartesianas locales centradas en cero, sin sistema de referencia geográfico;
- fuentes, equipos y destinos identificados mediante contratos genéricos;
- capacidades, estados y relaciones estadísticas definidos exclusivamente en el generador;
- número de registros y geometría espacial creados para el ejercicio;
- pruebas automáticas que rechazan fechas históricas y coordenadas con apariencia UTM.

El caso conserva relaciones pedagógicas —composiciones cerradas, granularidades,
dependencias temporales y consistencia entre tablas—, pero no conserva filas,
series, ubicaciones ni parámetros de una fuente industrial. Los datos no deben
interpretarse como descripción, aproximación o *benchmark* de una faena.

## Regeneración

Desde la raíz del proyecto Kedro:

```bash
uv run python scripts/generate_public_synthetic_data.py
uv run pytest
uv run kedro run --env test
```

La publicación debe regenerar también el explorador de código y Kedro Viz, y debe
construir este último sobre una carpeta vacía para evitar artefactos huérfanos.
