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

PATH_SAMPLES: str = "data/samples"
PATH_RESULTS: str = "data/results"

NET_LABEL: str = "NET"
LOGS_PATH: str = "logs/runtime"
PROFILING_PATH: str = "review/profiling"

CSV_EXTENSION: str = "csv"
HTML_EXTENSION: str = "html"
EXCEL_EXTENSION: str = "xlsx"

TYPE_TAG: str = "type"

# Tolerancia para considerar que dos pérdidas δ_k "coinciden" (absorbe los
# desempates entre óptimos degenerados: particiones distintas con igual pérdida).
DELTA_K_TOLERANCE: float = 1e-3

# Paleta cualitativa compartida por las vistas estática e interactiva; los
# bloques más allá del último color reutilizan la paleta de forma cíclica.
BLOCK_PALETTE: tuple[str, ...] = (
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3",
)
