"""
Implementa un dataset local para persistir objetos ``arviz.InferenceData`` en NetCDF.
"""

from pathlib import Path
from typing import Any

import arviz as az
from kedro.io import AbstractDataset


class InferenceDataDataset(AbstractDataset[Any, Any]):
    """
    Serializa los grupos posteriores de ArviZ sin acoplar la persistencia a un nodo.

    Parámetros:
    -------------
    filepath : ruta local del archivo NetCDF que almacena el objeto de inferencia.
    """

    def __init__(self, filepath: str):
        """
        Inicializa el dataset con la ruta del archivo NetCDF.

        Parámetros:
        -------------
        filepath : ruta local del archivo que se leerá o escribirá.

        Retorna:
        ---------
        None.
        """
        self._filepath = Path(filepath)

    def _load(self) -> Any:
        """
        Carga desde disco el objeto de inferencia serializado.

        Parámetros:
        -------------
        No aplica.

        Retorna:
        ---------
        Any : objeto ``arviz.InferenceData`` reconstruido desde NetCDF.
        """
        return az.from_netcdf(self._filepath)

    def _save(self, data: Any) -> None:
        """
        Guarda un objeto de inferencia en formato NetCDF y crea su directorio si es necesario.

        Parámetros:
        -------------
        data : objeto compatible con el método ``to_netcdf`` de ArviZ.

        Retorna:
        ---------
        None.
        """
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        data.to_netcdf(self._filepath)

    def _describe(self) -> dict[str, str]:
        """
        Describe la ubicación configurada para el dataset.

        Parámetros:
        -------------
        No aplica.

        Retorna:
        ---------
        dict[str, str] : metadatos con la ruta del archivo NetCDF.
        """
        return {"filepath": str(self._filepath)}

    def _exists(self) -> bool:
        """
        Comprueba si el archivo configurado existe en el sistema local.

        Parámetros:
        -------------
        No aplica.

        Retorna:
        ---------
        bool : ``True`` cuando el archivo existe y ``False`` en caso contrario.
        """
        return self._filepath.exists()
