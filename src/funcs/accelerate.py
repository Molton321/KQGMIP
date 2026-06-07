"""Optional Numba acceleration with a pure-NumPy fallback.

Phase 6 applies Numba (``nogil=True``) to a hot numeric loop only where it is
worth it: the **batch effect-EMD**, i.e. scoring many candidate distributions
against a single baseline at once. Releasing the GIL lets this kernel run inside
worker threads without contention, so it composes with the parallel candidate
evaluation (``src/funcs/parallel.py``).

Numba is an **optional** dependency (extra ``perf``); when it is not installed
the module transparently falls back to the vectorized NumPy implementation, so
the core never depends on it and the test gate stays green either way. Both
paths are numerically identical (the EMD-effect is an L1 sum of per-node
absolute differences).

    uv run --extra perf python -c "from src.funcs import accelerate; print(accelerate.BACKEND)"
"""

from typing import Any

import numpy as np
from numpy.typing import NDArray

try:  # pragma: no cover - import side effect depends on the environment
    import numba  # noqa: F401

    _HAS_NUMBA = True
except Exception:  # pragma: no cover
    _HAS_NUMBA = False

BACKEND: str = "numba" if _HAS_NUMBA else "numpy"


def _build_batch_emd_kernel() -> Any:  # pragma: no cover - only with numba installed
    """Compile the nogil/parallel Numba kernel for the batch effect-EMD."""
    from numba import njit, prange

    @njit(nogil=True, parallel=True, cache=True, fastmath=True)
    def _kernel(distributions: NDArray[np.float32], baseline: NDArray[np.float32]):
        rows = distributions.shape[0]
        cols = distributions.shape[1]
        out = np.empty(rows, dtype=np.float32)
        for i in prange(rows):
            acc = np.float32(0.0)
            for j in range(cols):
                diff = distributions[i, j] - baseline[j]
                acc += diff if diff >= 0 else -diff
            out[i] = acc
        return out

    return _kernel


_BATCH_EMD_KERNEL: Any = _build_batch_emd_kernel() if _HAS_NUMBA else None


def batch_effect_emd(
    distributions: NDArray[np.float32],
    baseline: NDArray[np.float32],
) -> NDArray[np.float32]:
    """Effect-EMD of each row of ``distributions`` against ``baseline``.

    Args:
        distributions: ``(batch, n)`` candidate marginal distributions.
        baseline: ``(n,)`` reference (subsystem) distribution.

    Returns:
        ``(batch,)`` array of L1 distances, identical under both backends.
    """
    rows = np.ascontiguousarray(distributions, dtype=np.float32)
    reference = np.ascontiguousarray(baseline, dtype=np.float32)
    if rows.ndim != 2:
        rows = rows.reshape(-1, reference.shape[0])
    if _BATCH_EMD_KERNEL is not None:
        return np.asarray(_BATCH_EMD_KERNEL(rows, reference), dtype=np.float32)
    return np.abs(rows - reference).sum(axis=1).astype(np.float32)
