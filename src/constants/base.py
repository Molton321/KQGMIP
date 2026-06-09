"""Core numeric, string, path and tag constants shared across the framework.

Centralizes every literal the pipeline relies on (axis indices, sentinel values,
project paths, profiling tags, the block color palette) so no module hard-codes a
magic value — the single source of truth required by the project conventions.
"""

from pathlib import Path

INFTY_POS: float = float("inf")

INT_ZERO: int = 0
INT_ONE: int = 1

FLOAT_ZERO: float = float(INT_ZERO)

BASE_TWO: int = 2

WIDTH_PADDING: int = 2

LAST_IDX: int = -1
ACTUAL = INT_ZERO
COLS_IDX = EFECTO = INT_ONE

STR_ZERO: str = "0"
STR_ONE: str = "1"

EMPTY_STR: str = ""
WHITESPACE: str = " "
COLON_DELIM: str = ","
VOID_STR: str = "∅"
ABC_START: str = "A"


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_TIMEOUT = 300

PATH_SAMPLES: Path = PROJECT_ROOT / "data" / "samples"
PATH_RESULTS: Path = PROJECT_ROOT / "data" / "results"
BENCHMARK_CSV: Path = PROJECT_ROOT / "data" / "results" / "benchmark_results_FINAL.csv"

NET_LABEL: str = "NET"
LOGS_PATH: str = "logs/runtime"
PROFILING_PATH: str = "review/profiling"

CSV_EXTENSION: str = "csv"
HTML_EXTENSION: str = "html"
EXCEL_EXTENSION: str = "xlsx"

TYPE_TAG: str = "type"
DELTA_K_TOLERANCE: float = 1e-3

BLOCK_PALETTE: tuple[str, ...] = (
    "#4C72B0",
    "#DD8452",
    "#55A868",
    "#C44E52",
    "#8172B3",
    "#937860",
    "#DA8BC3",
)
