"""Constants related to the evaluation grid."""

from src.constants.base import PATH_RESULTS

GRID_TEMPLATE_XLSX = PATH_RESULTS / "datos.xlsx"
GRID_RESULTS_XLSX = PATH_RESULTS / "resultados.xlsx"
GRID_SHEET_SUFFIX: str = "Elementos"
GRID_STATE_LABEL: str = "Estado inicial"
GRID_HEADER_LABEL: str = "#Prueba"
GRID_PURVIEW_COLUMN: int = 2
GRID_MECHANISM_COLUMN: int = 3
GRID_K_VALUES: tuple[int, ...] = (2, 3, 4, 5)
GRID_K_BASE_COLUMN: dict[int, int] = {2: 4, 3: 10, 4: 16, 5: 22}
GRID_FAMILY_OFFSET: dict[str, int] = {"QNodes": 0, "Geometric": 3}
GRID_FAMILY_STRATEGY: dict[str, str] = {"QNodes": "KQNodes", "Geometric": "KGeoMIP"}
