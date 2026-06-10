"""
Exact k-partition strategy using weak Stirling partitions.

This strategy exhaustively evaluates every k-partition of the subsystem's future and
present nodes, returning the one with the lowest δ_k. The search space is
constrained by using weak Stirling partitions, which allow empty blocks and thus
include the legacy semantics of sub_purview=∅ or sub_mechanism=∅. The strategy can
be run in parallel across multiple CPU cores, with an early exit if a perfect
partition (δ_k = 0) is found.

This is the *ground truth*: only feasible for small systems (it is the exact
optimum used to validate the heuristics), so it is the reference, not a production
strategy. The number of k-partitions of 2n atoms grows as the Stirling number
of the second kind S(2n, k), which is super-exponential — hence the n <= 6
ceiling in practice (doc §4.2). parallel=True distributes the candidate stream
across n_jobs processes (GIL is active, so processes not threads) with a shared
δ=0 early-exit, giving an empirical ~2-3x speedup with 4 jobs for n >= 6; it
does not change the result, only the wall time.

Usage::

    # exact reference for a small network (serial)
    ExhaustiveK(tpm, state, k=3).apply_strategy(cond, purview, mechanism)
    # same result, parallel across 4 processes
    ExhaustiveK(tpm, state, k=3, parallel=True, n_jobs=4).apply_strategy(...)
"""

import os
import time
from collections.abc import Generator
from itertools import permutations, product
from multiprocessing import shared_memory

import numpy as np
from joblib import Parallel, delayed
from more_itertools import set_partitions

from src.constants.base import COLS_IDX, NET_LABEL
from src.constants.strategies import EXACT_K_LABEL, EXACT_K_STRATEGY_TAG
from src.funcs.emd import delta_k
from src.funcs.format import fmt_kpartition
from src.funcs.parallel import (
    chunk_evenly,
    derive_seeds,
    limit_worker_threads,
    rebuild_system,
    shared_ndarray,
)
from src.middlewares.profile import profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution


def _weak_k_partitions(
    elements: tuple[int, ...], k: int
) -> Generator[tuple[tuple[int, ...], ...]]:
    """
    Yield every k-tuple of subsets that partitions elements allowing empty blocks.
    A weak k-partition is a list of k subsets that, taken together, are a
    partition of elements. Empty subsets are allowed. Order matters: the
    same partition expressed as (A, B) versus (B, A) is yielded twice.
    The whole universe may land in a single slot (the rest being empty),
    which is the legacy sub_purview=∅ or sub_mechanism=∅ semantics.
    """
    if k < 1:
        return

    elements_tuple = tuple(sorted(elements))

    for slot in range(k):
        blocks: list[tuple[int, ...]] = [tuple() for _ in range(k)]
        blocks[slot] = elements_tuple
        yield tuple(blocks)

    for r in range(2, min(k, len(elements_tuple)) + 1):
        for partition in set_partitions(elements_tuple, r):
            for assignment in product(range(k), repeat=r):
                if len(set(assignment)) != r:
                    continue

                placed: list[tuple[int, ...]] = [tuple() for _ in range(k)]

                for slot, block in zip(assignment, partition, strict=False):
                    placed[slot] = tuple(sorted(int(i) for i in block))
                yield tuple(placed)


def _generate_candidates(
    future_options: list[tuple[tuple[int, ...], ...]],
    present_options: list[tuple[tuple[int, ...], ...]],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
) -> Generator[KPartition]:
    """
    Yield the unique valid k-partitions for a slice of future.
    Pairs each future weak-partition with every present weak-partition across
    all permutations, validating and de-duplicating. Module-level so it is
    picklable and reusable by both the sequential and the worker paths; the
    de-dup set is local, which is correct because distinct future_options
    yield disjoint candidate sets.
    """
    seen: set[tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]] = set()

    for future_blocks in future_options:
        for present_blocks in present_options:
            for perm in permutations(range(k)):
                blocks: list[tuple[tuple[int, ...], tuple[int, ...]]] = [
                    (tuple(future_blocks[idx]), tuple(present_blocks[perm[idx]]))
                    for idx in range(k)
                ]
                try:
                    candidate = KPartition.from_blocks(
                        blocks=blocks,
                        future_universe=future_universe,
                        present_universe=present_universe,
                    )
                except ValueError:
                    continue
                if candidate.signature in seen:
                    continue
                seen.add(candidate.signature)
                yield candidate


def _exact_search_worker(
    shm_name: str,
    shape: tuple[int, ...],
    dtype: np.dtype,
    dims: np.ndarray,
    indices: np.ndarray,
    initial_state: np.ndarray,
    baseline: np.ndarray,
    k: int,
    future_slice: list[tuple[tuple[int, ...], ...]],
    present_options: list[tuple[tuple[int, ...], ...]],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    seed: int,
) -> tuple[float, KPartition | None, np.ndarray]:
    """
    Generate and evaluate candidates for a slice of future weak-partitions,
    returning the best result.
    """
    limit_worker_threads()
    np.random.seed(seed)

    shm = shared_memory.SharedMemory(name=shm_name)
    try:
        flat = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
        system = rebuild_system(flat, dims, indices, initial_state)

        best_loss = float("inf")
        best_partition: KPartition | None = None
        best_distribution = np.array([], dtype=np.float32)
        for candidate in _generate_candidates(
            future_slice, present_options, future_universe, present_universe, k
        ):
            loss, distribution = delta_k(
                system, candidate, baseline_distribution=baseline
            )
            if loss < best_loss:
                best_loss = loss
                best_partition = candidate
                best_distribution = distribution

                if loss == 0.0:
                    break

        return best_loss, best_partition, best_distribution
    finally:
        shm.close()


class ExhaustiveK(SIA):
    """Exact k-partition strategy using weak Stirling partitions."""

    def __init__(
        self,
        tpm: np.ndarray,
        initial_state: str,
        k: int,
        parallel: bool = False,
        n_jobs: int = -1,
    ) -> None:
        """Build the exact strategy.

        Args:
            tpm: transition probability matrix of the candidate system.
            initial_state: binary initial state string.
            k: number of blocks of the k-partition to search for.
            parallel: distribute the candidate stream across processes when True
                (same result, lower wall time for n >= 6).
            n_jobs: number of worker processes when parallel (-1 = all cores).
        """
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(EXACT_K_STRATEGY_TAG)
        self.k = k
        self.parallel = parallel
        self.n_jobs = n_jobs
        self.best_partition: KPartition | None = None

    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Run exact search for the best k-partition under the current subsystem."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        future_universe = tuple(
            int(i) for i in self.sia_subsystem.ncube_indices.tolist()
        )
        present_universe = tuple(int(i) for i in self.sia_subsystem.ncube_dims.tolist())

        if self.k < 2:
            raise ValueError("k must be >= 2.")

        baseline = self.sia_marginal_dists
        if self.parallel:
            best_loss, best_distribution = self._search_parallel(
                future_universe, present_universe, baseline
            )
        else:
            best_loss, best_distribution = self._search_sequential(
                future_universe, present_universe, baseline
            )

        if self.best_partition is None:
            raise RuntimeError(
                "ExactK failed to generate any valid k-partition candidate."
            )

        return Solution(
            strategy=f"{EXACT_K_LABEL}(k={self.k})",
            loss=float(best_loss),
            subsystem_distribution=baseline,
            partition_distribution=best_distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(self.best_partition.signature),
        )

    def _search_sequential(
        self,
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
        baseline: np.ndarray,
    ) -> tuple[float, np.ndarray]:
        """Evaluate every candidate in-process (with an early exit at δ_k = 0)."""
        best_loss = np.inf
        best_distribution = np.array([], dtype=np.float32)

        for candidate in self._candidate_partitions(future_universe, present_universe):
            loss, partition_distribution = delta_k(
                self.sia_subsystem, candidate, baseline_distribution=baseline
            )
            if loss < best_loss:
                best_loss = loss
                best_distribution = partition_distribution
                self.best_partition = candidate

                if loss == 0.0:
                    break

        return float(best_loss), best_distribution

    def _search_parallel(
        self,
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
        baseline: np.ndarray,
    ) -> tuple[float, np.ndarray]:
        """
        Evaluate candidates in parallel batches, with an early exit at δ_k = 0.
        """
        future_options = list(_weak_k_partitions(future_universe, self.k))
        present_options = list(_weak_k_partitions(present_universe, self.k))

        subsystem = self.sia_subsystem
        flat = np.ascontiguousarray(
            np.stack([cube.data.ravel() for cube in subsystem.ncubes]), dtype=np.float32
        )
        dims = np.asarray(subsystem.ncube_dims, dtype=np.int8)
        indices = np.asarray(subsystem.ncube_indices, dtype=np.int8)
        initial_state = np.asarray(subsystem.initial_state, dtype=np.int8)

        workers = (os.cpu_count() or 1) if self.n_jobs in (-1, 0) else self.n_jobs
        chunks = chunk_evenly(future_options, workers)
        seeds = derive_seeds(len(chunks))

        with shared_ndarray(flat) as (name, shape, dtype):
            results = Parallel(n_jobs=workers, backend="loky")(
                delayed(_exact_search_worker)(
                    name,
                    shape,
                    dtype,
                    dims,
                    indices,
                    initial_state,
                    baseline,
                    self.k,
                    chunk,
                    present_options,
                    future_universe,
                    present_universe,
                    seed,
                )
                for chunk, seed in zip(chunks, seeds, strict=True)
            )

        best_loss = np.inf
        best_distribution = np.array([], dtype=np.float32)

        for loss, partition, distribution in results:
            if loss < best_loss:
                best_loss = loss
                self.best_partition = partition
                best_distribution = distribution
        return float(best_loss), best_distribution

    def _candidate_partitions(
        self,
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
    ) -> Generator[KPartition]:
        """
        Generate all valid k-partitions of the subsystem's future and present nodes.
        """
        future_options = list(_weak_k_partitions(future_universe, self.k))
        present_options = list(_weak_k_partitions(present_universe, self.k))
        yield from _generate_candidates(
            future_options, present_options, future_universe, present_universe, self.k
        )
