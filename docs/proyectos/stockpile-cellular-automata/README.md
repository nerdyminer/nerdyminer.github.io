# Autómata celular continuo 3D para un acopio de mineral

Esta es la edición pública y pedagógica del segundo proyecto de NerdyMiner. Implementa en Python una versión compacta del autómata celular continuo descrito por Ye, Hilden y Yahyaei (2022, 2023), con una separación explícita entre contratos, lógica científica, activos orquestados y visualización.

La publicación utiliza un escenario sintético con calendario, geometría, señales y equipos ficticios. `public_minute_series` lee esta ventana pedagógica determinista y las pruebas verifican que se mantenga dentro de sus rangos públicos sin introducir identificadores industriales.

## Ejecutar

```bash
uv sync --group dev
uv run pytest
uv run dagster asset materialize --select '*' -m stockpile_ca.definitions
uv run dagster dev -m stockpile_ca.definitions
```

La aplicación publicada vive en `app/`. Descarga y decodifica bajo demanda los cuadros binarios sintéticos de cada día para cualquier ventana de hasta catorce días; no reconstruye la superficie en el navegador.

La interfaz oficial de Dagster se levanta con el último comando y requiere un backend local. La versión navegable publicada en `dagster/` se regenera con `uv run python scripts/build_dagster_snapshot.py`; el script extrae activos, checks, grupos y dependencias desde `Definitions.resolve_asset_graph()` en vez de mantener un diagrama paralelo.

## Arquitectura

```text
escenario sintético -> Polars -> contratos Pydantic -> activos Dagster
                                    |                    |
                                    v                    v
                            dominio científico       asset checks
                                    |
                                    v
                       estados 3D + reconciliación -> visor React/canvas
```

Los artículos originales se reconocen como origen metodológico, no como código copiado. La réplica pública utiliza Python, NumPy, Polars, Pydantic y Dagster; los autores reportan implementaciones en MATLAB y C++.
