"""Fill the official evaluation grid (DatosPruebas2026_1.xlsx) with KQNodes/KGeoMIP.

Usage:
    uv run scripts/fill_official_grid.py --sheets 10A-Elementos
    uv run scripts/fill_official_grid.py            # every sheet
"""

import argparse
import sys
from pathlib import Path

from src.constants.grid import GRID_RESULTS_XLSX, GRID_TEMPLATE_XLSX
from src.funcs.grid import fill_grid
from src.models.base.application import application

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    """Parse options and fill the requested sheets of the official grid."""
    parser = argparse.ArgumentParser(description="Fill the official k-partition grid.")
    parser.add_argument(
        "--sheets",
        nargs="*",
        default=None,
        help="Sheet names to fill (default: all *-Elementos sheets).",
    )
    args = parser.parse_args()
    application.disable_profiling()
    fill_grid(GRID_TEMPLATE_XLSX, GRID_RESULTS_XLSX, sheet_names=args.sheets)


if __name__ == "__main__":
    main()
