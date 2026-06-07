"""Process-parallel primitives: shared memory, seed control, thread affinity.

Phase 6 PCD layer. The GIL is active, so CPU-bound candidate evaluation is
parallelized across worker **processes** (threads would not help). This module
provides the reusable building blocks; the parallel driving loops live in the
strategies that own the candidate generation (e.g. ``ExhaustiveK``), so that
both *generation* and *evaluation* run in the workers — parallelizing only the
evaluation leaves the sequential generation as the bottleneck.

Three official DoD requirements are met here:

- **SharedMemory for heavy structures:** the subsystem's stacked n-cube tensors
  (the only large array) are placed in ``multiprocessing.shared_memory`` once and
  attached read-only by every worker, avoiding the IPC cost of pickling
  megabytes per task.
- **Thread-affinity / no oversubscription:** each worker pins BLAS/OpenMP pools
  to one thread, so ``n_jobs`` processes do not each spawn a full thread pool.
- **Deterministic seeds across processes:** per-worker seeds are spawned from a
  single ``SeedSequence(application.numpy_seed)``, so stochastic behaviour is
  reproducible regardless of how the work is sharded.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

import numpy as np
from numpy.typing import NDArray

from src.models.base.application import application


def derive_seeds(n_workers: int) -> list[int]:
    """Independent, reproducible seeds for ``n_workers`` from the global seed."""
    root = np.random.SeedSequence(application.numpy_seed)
    return [int(child.generate_state(1)[0]) for child in root.spawn(n_workers)]


def limit_worker_threads() -> None:
    """Pin BLAS/OpenMP pools to one thread to prevent oversubscription.

    Uses ``threadpoolctl`` when available (extra ``perf``); otherwise sets the
    standard environment variables. Called at the start of every worker.
    """
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ.setdefault(variable, "1")
    try:  # pragma: no cover - only when threadpoolctl is installed
        import threadpoolctl

        threadpoolctl.threadpool_limits(1)
    except Exception:  # pragma: no cover
        pass


def chunk_evenly(items: list, n_chunks: int) -> list[list]:
    """Split ``items`` into at most ``n_chunks`` near-even contiguous chunks."""
    if n_chunks <= 1 or len(items) <= 1:
        return [items]
    size = max(1, (len(items) + n_chunks - 1) // n_chunks)
    return [items[i : i + size] for i in range(0, len(items), size)]


@contextmanager
def shared_ndarray(array: np.ndarray) -> Generator[tuple[str, tuple[int, ...], np.dtype]]:
    """Copy ``array`` into shared memory; yield ``(name, shape, dtype)``.

    The block is unlinked on exit, so workers must attach (and detach) only
    within the ``with`` body.
    """
    from multiprocessing import shared_memory

    shm = shared_memory.SharedMemory(create=True, size=max(int(array.nbytes), 1))
    try:
        view: NDArray = np.ndarray(array.shape, dtype=array.dtype, buffer=shm.buf)
        view[...] = array
        yield shm.name, array.shape, array.dtype
    finally:
        shm.close()
        shm.unlink()


def rebuild_system(
    flat: np.ndarray,
    dims: np.ndarray,
    indices: np.ndarray,
    initial_state: np.ndarray,
):
    """Rebuild a ``System`` from stacked flat n-cube data (worker side)."""
    from src.models.core.ncube import NCube
    from src.models.core.system import System

    shape = (2,) * int(dims.size)
    system = System.__new__(System)
    system.initial_state = initial_state
    system.memo = {}
    system.ncubes = tuple(
        NCube(index=int(indices[i]), dims=dims, data=flat[i].reshape(shape))
        for i in range(int(indices.size))
    )
    return system
