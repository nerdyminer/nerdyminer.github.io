"""
Proporciona el punto de entrada del paquete compatible con la CLI de Kedro.
"""

from pathlib import Path

from kedro.framework.cli.utils import KedroCliError
from kedro.framework.startup import bootstrap_project


def main() -> None:
    """
    Inicializa el proyecto desde el directorio de trabajo para delegar su ejecución a Kedro.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La función inicializa el proyecto o levanta ``KedroCliError`` si la ruta no es válida.
    """
    try:
        bootstrap_project(Path.cwd())
    except Exception as exc:  # pragma: no cover - mensaje de conveniencia para CLI
        raise KedroCliError("Ejecuta este comando desde la raíz del proyecto Kedro.") from exc


if __name__ == "__main__":
    main()
