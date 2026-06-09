"""Layout constants of the official evaluation grid (``DatosPruebas2026_1.xlsx``).

Single source of truth for the workbook format shared by the CLI batch mode,
``scripts/fill_official_grid.py`` and the Streamlit UI (FASE 11): sheet naming,
anchor labels, column layout of the k/strategy blocks and the default
template/results paths. The numbers were validated against the official
template (Fase 10, bitácora 2026-06-09) — the template itself is never
overwritten; results go to a separate workbook.
"""

from src.constants.base import PATH_RESULTS

GRID_TEMPLATE_XLSX = PATH_RESULTS / "DatosPruebas2026_1.xlsx"
"""Official evaluation grid template (read-only input)."""

GRID_RESULTS_XLSX = PATH_RESULTS / "Resultados_DatosPruebas2026_1.xlsx"
"""Results workbook (a filled copy of the template; the template is never touched)."""

GRID_SHEET_SUFFIX: str = "Elementos"
"""Suffix identifying the per-network test sheets (e.g. ``25A-Elementos``)."""

GRID_STATE_LABEL: str = "Estado inicial"
"""Column-A anchor of the row holding the candidate initial state."""

GRID_HEADER_LABEL: str = "#Prueba"
"""Column-A anchor of the test-table header row (tests start on the next row)."""

GRID_PURVIEW_COLUMN: int = 2
"""1-based column of the purview (``Alcance``) letter mask."""

GRID_MECHANISM_COLUMN: int = 3
"""1-based column of the mechanism (``Mecanismo``) letter mask."""

GRID_K_VALUES: tuple[int, ...] = (2, 3, 4, 5)
"""The k-partition orders the grid evaluates per subsystem."""

GRID_K_BASE_COLUMN: dict[int, int] = {2: 4, 3: 10, 4: 16, 5: 22}
"""1-based column of the QNodes ``Partición`` cell for each k block.

Each block spans six columns: QNodes (Partición, Pérdida, Tiempo) followed by
Geometric (Partición, Pérdida, Tiempo).
"""

GRID_FAMILY_OFFSET: dict[str, int] = {"QNodes": 0, "Geometric": 3}
"""Column offset of each strategy family inside a k block."""

GRID_FAMILY_STRATEGY: dict[str, str] = {"QNodes": "KQNodes", "Geometric": "KGeoMIP"}
"""Maps the grid's column family to the project's k-partition strategy name."""
