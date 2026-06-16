"""Sentinel values and logging/profiling tags for the SIA pipeline."""

import numpy as np

DUMMY_EMD: int = -1
DUMMY_ARR: np.ndarray = np.zeros(1, dtype=np.float32)
ERROR_PARTITION: str = "No hay suficientes elementos para particionar.\n"
DUMMY_PARTITION: str = "NO-PARTITION\n"

SIA_LABEL: str = "sia"
SIA_PREPARATION_TAG: str = f"{SIA_LABEL}_preparation"
