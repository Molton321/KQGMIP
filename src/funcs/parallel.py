"""Process-parallel primitives: shared memory, seed control, thread affinity."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from multiprocessing import shared_memory

import numpy as np
import threadpoolctl
from numpy.typing import NDArray

from src.models.base.application import application
from src.models.core.ncube import NCube
from src.models.core.system import System


def derive_seeds(n_workers: int) -> list[int]:
    """Derive a list of seeds for worker processes from the application's base seed."""
    root = np.random.SeedSequence(application.numpy_seed)
    return [int(child.generate_state(1)[0]) for child in root.spawn(n_workers)]


def limit_worker_threads() -> None:
    """
    Limit the number of threads used by worker processes to 1 to avoid oversubscription.
    """
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ.setdefault(variable, "1")
    try:
        threadpoolctl.threadpool_limits(1)
    except Exception:
        pass


def chunk_evenly(items: list, n_chunks: int) -> list[list]:
    """Split a list into n_chunks as evenly as possible."""
    if n_chunks <= 1 or len(items) <= 1:
        return [items]
    size = max(1, (len(items) + n_chunks - 1) // n_chunks)
    return [items[i : i + size] for i in range(0, len(items), size)]


@contextmanager
def shared_ndarray(
    array: np.ndarray,
) -> Generator[tuple[str, tuple[int, ...], np.dtype]]:
    """Context manager for sharing a NumPy array in shared memory.
    Yields the name of the shared memory block, the shape, and the dtype,
    which can be used to reconstruct the array in another process.
    Cleans up the shared memory block when done.
    """
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
    """Reconstruct a System from shared memory arrays."""
    shape = (2,) * int(dims.size)
    system = System.__new__(System)
    system.initial_state = initial_state
    system.memo = {}
    system.ncubes = tuple(
        NCube(index=int(indices[i]), dims=dims, data=flat[i].reshape(shape))
        for i in range(int(indices.size))
    )
    return system
