"""Sentinel values and logging/profiling tags for the SIA pipeline.

Dummy EMD/array placeholders for empty solutions, the partition error strings and
the ``sia`` preparation tags consumed by the loggers and the ``@profile`` wrapper.
"""

import numpy as np

DUMMY_EMD: int = -1
DUMMY_ARR: np.ndarray = np.zeros(1, dtype=np.float32)
ERROR_PARTITION: str = "No hay suficientes elementos para particionar.\n"
DUMMY_PARTITION: str = "NO-PARTITION\n"

SIA_LABEL: str = "sia"
SIA_PREPARATION_TAG: str = f"{SIA_LABEL}_preparation"


PYPHI_LABEL: str = "Pyphi"
