"""Standardized reader/writer/runner for the official evaluation grid (FASE 11).

One place implementing the ``.xlsx`` contract of the project: the **input** is
the official template format (``DatosPruebas2026_1.xlsx``: one ``*-Elementos``
sheet per network with the candidate initial state and ~50 purview/mechanism
test rows) and the **output** is a filled copy of that same workbook with the
``Partición / Pérdida / Tiempo`` cells of the QNodes and Geometric families
completed for k ∈ {2,3,4,5}. The CLI batch mode (``main_batch.py``), the
dedicated script (``scripts/fill_official_grid.py``) and the Streamlit UI all
delegate here, so the format is parsed and produced in exactly one module
(layout constants in ``src/constants/grid.py``).

The grid convention was cross-validated against ``Pruebas_Metodo2.xlsx``
(known GeoMIP/PyPhi losses, Fase 10): candidate state = the sheet's
``Estado inicial``, background condition = all-ones, subsystem = the
purview/mechanism letter masks.
"""

import contextlib
import io
import string
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from src.constants.grid import (
    GRID_FAMILY_OFFSET,
    GRID_FAMILY_STRATEGY,
    GRID_HEADER_LABEL,
    GRID_K_BASE_COLUMN,
    GRID_K_VALUES,
    GRID_MECHANISM_COLUMN,
    GRID_PURVIEW_COLUMN,
    GRID_SHEET_SUFFIX,
    GRID_STATE_LABEL,
)


@dataclass(frozen=True)
class GridTest:
    """One test row of a grid sheet: purview/mechanism letter masks + bit masks."""

    row: int
    purview_letters: str
    mechanism_letters: str
    purview_mask: str
    mechanism_mask: str


@dataclass(frozen=True)
class GridSheet:
    """One parsed ``*-Elementos`` sheet: network metadata plus its test rows."""

    name: str
    initial_state: str
    page: str
    header_row: int
    tests: tuple[GridTest, ...]

    @property
    def num_nodes(self) -> int:
        """Network size n (length of the candidate initial state)."""
        return len(self.initial_state)


def letters_to_mask(letters: str, num_nodes: int) -> str:
    """Convert a purview/mechanism letter string (``"ACEGI"``) to an n-bit mask."""
    bits = ["0"] * num_nodes
    for char in str(letters).strip():
        bits[string.ascii_uppercase.index(char)] = "1"
    return "".join(bits)


def grid_sheet_names(path: Path) -> list[str]:
    """Return the ``*-Elementos`` sheet names of a grid workbook."""
    book = load_workbook(path, read_only=True)
    try:
        return [name for name in book.sheetnames if name.strip().endswith(GRID_SHEET_SUFFIX)]
    finally:
        book.close()


def read_grid_sheet(path: Path, sheet_name: str) -> GridSheet:
    """Parse one grid sheet into its standardized representation.

    Anchors are located by their column-A labels (``Estado inicial`` and
    ``#Prueba``); test rows run from the row after the header until the first
    row without both letter masks.

    Raises:
        ValueError: if an anchor is missing or a letter mask exceeds n.
    """
    book = load_workbook(path, read_only=True)
    try:
        sheet = book[sheet_name]
        initial_state = ""
        header_row = 0
        for row in range(1, 12):
            label = sheet.cell(row=row, column=1).value
            if label == GRID_STATE_LABEL:
                initial_state = str(sheet.cell(row=row, column=GRID_PURVIEW_COLUMN).value).strip()
            elif label == GRID_HEADER_LABEL:
                header_row = row
                break
        if not initial_state or not header_row:
            raise ValueError(
                f"La hoja '{sheet_name}' no tiene las anclas "
                f"'{GRID_STATE_LABEL}' / '{GRID_HEADER_LABEL}'."
            )

        num_nodes = len(initial_state)
        tests: list[GridTest] = []
        row = header_row + 1
        while True:
            purview_letters = sheet.cell(row=row, column=GRID_PURVIEW_COLUMN).value
            mechanism_letters = sheet.cell(row=row, column=GRID_MECHANISM_COLUMN).value
            if purview_letters in (None, "") or mechanism_letters in (None, ""):
                break
            tests.append(
                GridTest(
                    row=row,
                    purview_letters=str(purview_letters).strip(),
                    mechanism_letters=str(mechanism_letters).strip(),
                    purview_mask=letters_to_mask(str(purview_letters), num_nodes),
                    mechanism_mask=letters_to_mask(str(mechanism_letters), num_nodes),
                )
            )
            row += 1

        page = next(char for char in sheet_name if char.isalpha())
        return GridSheet(
            name=sheet_name,
            initial_state=initial_state,
            page=page,
            header_row=header_row,
            tests=tuple(tests),
        )
    finally:
        book.close()


class GridResultsWriter:
    """Incremental writer for the results workbook (template never modified).

    Opens the results workbook if it exists (resumable runs) or a fresh copy of
    the template otherwise, and exposes per-cell-group operations: which k
    values are still missing for a (row, family) and writing one result triple.
    """

    def __init__(self, template_path: Path, output_path: Path) -> None:
        """Load the output workbook (or seed it from the template)."""
        self.output_path = output_path
        self.book = load_workbook(output_path if output_path.exists() else template_path)

    def missing_ks(self, sheet_name: str, row: int, family: str) -> tuple[int, ...]:
        """Return the k values whose loss cell is still empty for this row/family."""
        sheet = self.book[sheet_name]
        offset = GRID_FAMILY_OFFSET[family]
        return tuple(
            k
            for k in GRID_K_VALUES
            if sheet.cell(row=row, column=GRID_K_BASE_COLUMN[k] + offset + 1).value in (None, "")
        )

    def write_result(
        self,
        sheet_name: str,
        row: int,
        family: str,
        k: int,
        partition: str,
        loss: float,
        seconds: float,
    ) -> None:
        """Write one ``Partición / Pérdida / Tiempo`` cell group."""
        sheet = self.book[sheet_name]
        base = GRID_K_BASE_COLUMN[k] + GRID_FAMILY_OFFSET[family]
        sheet.cell(row=row, column=base).value = partition
        sheet.cell(row=row, column=base + 1).value = round(float(loss), 8)
        sheet.cell(row=row, column=base + 2).value = round(float(seconds), 4)

    def save(self) -> None:
        """Persist the workbook to the output path."""
        self.book.save(self.output_path)


def fill_grid(
    template_path: Path,
    output_path: Path,
    sheet_names: list[str] | None = None,
    k_values: tuple[int, ...] = GRID_K_VALUES,
    progress: Callable[[str], None] = print,
) -> None:
    """Run KQNodes + KGeoMIP over a grid workbook and fill the results copy.

    For every test row and strategy family the expensive preparation runs
    **once** and every missing k reuses it (``apply_strategy_for_ks``,
    FASE 11). Progress is saved after each row, so interrupted runs resume by
    skipping already-filled loss cells.

    Args:
        template_path: Official grid template (read-only).
        output_path: Results workbook (created from the template if absent).
        sheet_names: Sheets to fill (default: every ``*-Elementos`` sheet).
        k_values: Subset of k blocks to fill (default: the official 2..5).
        progress: Sink for per-row progress lines (CLI: ``print``; UI: callback).
    """
    from src.controllers.manager import Manager
    from src.funcs.runner import build_strategy
    from src.models.base.application import application

    writer = GridResultsWriter(template_path, output_path)
    names = sheet_names or grid_sheet_names(template_path)

    for sheet_name in names:
        sheet = read_grid_sheet(template_path, sheet_name)
        application.set_sample_network_page(sheet.page)
        condition = "1" * sheet.num_nodes
        tpm = Manager(sheet.initial_state).load_network()
        progress(f"=== {sheet_name} (n={sheet.num_nodes}, estado={sheet.initial_state}) ===")

        for test in sheet.tests:
            for family, strategy_name in GRID_FAMILY_STRATEGY.items():
                missing = tuple(
                    k for k in writer.missing_ks(sheet_name, test.row, family) if k in k_values
                )
                if not missing:
                    continue
                with contextlib.redirect_stdout(io.StringIO()):
                    analyzer = build_strategy(
                        strategy_name, tpm, sheet.initial_state, missing[0], "spectral"
                    )
                    solutions = analyzer.apply_strategy_for_ks(
                        condition, test.purview_mask, test.mechanism_mask, missing
                    )
                for k, solution in solutions.items():
                    writer.write_result(
                        sheet_name,
                        test.row,
                        family,
                        k,
                        solution.partition,
                        float(solution.loss),
                        float(solution.execution_time),
                    )
            writer.save()
            progress(
                f"  {sheet_name} fila {test.row - sheet.header_row}: "
                f"{test.purview_letters}|{test.mechanism_letters} lista"
            )
    writer.save()
    progress(f"Resultados guardados en {output_path}")
