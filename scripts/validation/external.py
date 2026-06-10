"""Cross-validation against the professor's original project (Invariante 3/4).

Validates the project's results against the only external reference of record,
the original project handed out by the professor (.core/core_00, source:
https://github.com/JuManoel/projecto-analisis-20261):

1. TPM samples: the network files we sample from are verified byte-identical
   to the ones shipped in the original project.
2. GeoMIP results: the rows of the original resultados_Geometric.xlsx
   (N15A, continuous TPM) are reproduced with our GeometricSIA within
   float32 tolerance.
3. Stored partitions: every partition written to our results workbook is
   parsed back, validated as a strict k-partition and re-scored with the
   official delta_k, so the partitions themselves are checked, not only their
   reported loss/time.

    uv run scripts/validate.py external                  # reproduce the original
    uv run scripts/validate.py external --rows 12
    uv run scripts/validate.py external --verify-partitions
"""

import argparse
import contextlib
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# isort: split
from openpyxl import load_workbook

from src.constants.base import PROJECT_ROOT
from src.constants.grid import (
    GRID_FAMILY_OFFSET,
    GRID_K_BASE_COLUMN,
    GRID_K_VALUES,
    GRID_RESULTS_XLSX,
)
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.models.base.application import application

PATH_CORE = PROJECT_ROOT / ".core" / "core_00" / "GeoMIP"
OURS_XLSX = GRID_RESULTS_XLSX

LOSS_EPS = 1e-6
"""Comparison tolerance: above the 8-decimal rounding of our stored losses."""


def _load_workbook_retrying(path: Path, attempts: int = 3):
    """Open a workbook retrying briefly: the batch filler saves it row by row,
    so a concurrent read can transiently hit a half-written zip."""
    for attempt in range(attempts):
        try:
            return load_workbook(path, read_only=True)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2)


def reproduce(num_rows: int) -> None:
    """Reproduce the original resultados_Geometric.xlsx rows with GeometricSIA."""
    sample_ours = PROJECT_ROOT / "data" / "samples" / "N15A.csv"
    sample_core = PATH_CORE / "data" / "samples" / "N15A.csv"
    identical = sample_ours.read_bytes() == sample_core.read_bytes()
    print(
        f"== Proyecto original (.core/core_00): TPM N15A idéntica byte a byte: {identical} =="
    )

    book = load_workbook(
        PATH_CORE / "results" / "resultados_Geometric.xlsx", read_only=True
    )
    sheet = book["Sheet1"]
    cases = []
    for row in range(2, 2 + num_rows):
        purview = str(sheet.cell(row=row, column=2).value)
        mechanism = str(sheet.cell(row=row, column=3).value)
        loss = float(str(sheet.cell(row=row, column=5).value).replace(",", "."))
        cases.append((purview, mechanism, loss))
    book.close()

    application.set_sample_network_page("A")
    state = "1" + "0" * 14
    tpm = Manager(state).load_network()
    condition = "1" * 15
    matched = 0
    for purview, mechanism, expected in cases:
        with contextlib.redirect_stdout(io.StringIO()):
            solution = GeometricSIA(tpm, state).apply_strategy(
                condition, purview, mechanism
            )
        ok = abs(float(solution.loss) - expected) < 1e-4
        matched += ok
        print(
            f"  {purview}|{mechanism}: original={expected:.10f} "
            f"nuestra={float(solution.loss):.10f} -> {'OK' if ok else 'DIFIERE'}"
        )
    print(
        f"  Reproducidas {matched}/{len(cases)} filas (tolerancia float32 sobre TPM continua)."
    )


def verify_workbook_partitions(sheet_names: list[str] | None = None) -> None:
    """Re-evaluate every stored partition of the results workbook.

    For each filled (row, family, k) cell the partition string is parsed back
    into blocks, validated as a strict k-partition (coverage/disjointness per
    the official definition) and re-scored with delta_k on the reconstructed
    subsystem; the result must match the stored loss. This checks the
    partitions themselves, not just their reported numbers.
    """
    import contextlib as _ctx

    from src.funcs.emd import delta_k
    from src.funcs.grid import read_grid_sheet
    from src.models.base.sia import SIA
    from src.models.core.partition import KPartition

    class _Probe(SIA):
        """Minimal SIA subclass used only to build subsystems."""

        def apply_strategy(self, *args, **kwargs):
            """Unused; required by the abstract interface."""
            raise NotImplementedError

    def parse_partition(text: str) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        """Parse fmt_kpartition lines (B1: abc | ABC) into index blocks."""
        blocks = []
        for line in str(text).strip().splitlines():
            _, _, body = line.partition(":")
            mechanism_text, _, purview_text = body.partition("|")
            mechanism = tuple(
                ord(c) - 97
                for c in mechanism_text.strip()
                if c.isalpha() and c.islower()
            )
            purview = tuple(
                ord(c) - 65 for c in purview_text.strip() if c.isalpha() and c.isupper()
            )
            blocks.append((purview, mechanism))
        return blocks

    book = _load_workbook_retrying(OURS_XLSX)
    names = sheet_names or [
        s for s in book.sheetnames if s.strip().endswith("Elementos")
    ]
    book.close()

    print(
        "== Verificación de particiones del workbook (re-evaluación con δ oficial) =="
    )
    for sheet_name in names:
        sheet = read_grid_sheet(OURS_XLSX, sheet_name)
        application.set_sample_network_page(sheet.page)
        tpm = Manager(sheet.initial_state).load_network()
        condition = "1" * sheet.num_nodes

        book = _load_workbook_retrying(OURS_XLSX)
        cells = book[sheet_name]
        checked = mismatched = invalid = 0
        for test in sheet.tests:
            probe = _Probe(tpm, sheet.initial_state)
            with _ctx.redirect_stdout(io.StringIO()):
                probe.sia_prepare_subsystem(
                    condition, test.purview_mask, test.mechanism_mask
                )
            subsystem = probe.sia_subsystem
            future_universe = tuple(int(i) for i in subsystem.ncube_indices.tolist())
            present_universe = tuple(int(i) for i in subsystem.ncube_dims.tolist())

            for k in GRID_K_VALUES:
                for family, offset in GRID_FAMILY_OFFSET.items():
                    base = GRID_K_BASE_COLUMN[k] + offset
                    partition_text = cells.cell(row=test.row, column=base).value
                    stored_loss = cells.cell(row=test.row, column=base + 1).value
                    if partition_text in (None, "") or stored_loss in (None, ""):
                        continue
                    checked += 1
                    try:
                        partition = KPartition.from_blocks(
                            parse_partition(partition_text),
                            future_universe,
                            present_universe,
                        )
                    except ValueError as error:
                        invalid += 1
                        print(
                            f"  INVÁLIDA {sheet_name} fila {test.row} {family} k={k}: {error}"
                        )
                        continue
                    loss, _ = delta_k(
                        subsystem,
                        partition,
                        baseline_distribution=probe.sia_marginal_dists,
                    )
                    if abs(float(loss) - float(stored_loss)) > LOSS_EPS:
                        mismatched += 1
                        print(
                            f"  DESAJUSTE {sheet_name} fila {test.row} {family} k={k}: "
                            f"celda={stored_loss} re-evaluada={float(loss):.8f}"
                        )
        book.close()
        print(
            f"  {sheet_name}: {checked} celdas verificadas | inválidas {invalid} | "
            f"desajustes de pérdida {mismatched}"
        )


def main() -> None:
    """Run the cross-validation against the original project."""
    parser = argparse.ArgumentParser(
        description="Cross-validation vs the professor's original project."
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=6,
        help="Rows of resultados_Geometric to reproduce.",
    )
    parser.add_argument(
        "--verify-partitions",
        nargs="*",
        default=None,
        metavar="SHEET",
        help="Re-evaluate the stored partitions of the results workbook "
        "(all sheets when no names are given).",
    )
    args = parser.parse_args()
    application.disable_profiling()

    if args.verify_partitions is not None:
        verify_workbook_partitions(args.verify_partitions or None)
        return

    reproduce(args.rows)


if __name__ == "__main__":
    main()
