"""Exact k-partition strategy using Stirling partitions.

This strategy is intended as ground truth for small systems. It enumerates
all valid pairings of:
- k partitions over future indices (with empty blocks allowed),
- k partitions over present indices (with empty blocks allowed),
and evaluates each candidate with ``delta_k``.

Empty blocks per dimension are allowed so that the k=2 case reduces exactly
to the legacy bipartition semantics (where ``sub_purview`` and ``sub_mechanism``
can each be empty as long as one side is non-empty).
"""

import time
from collections.abc import Generator
from itertools import permutations, product

import numpy as np
from more_itertools import set_partitions

from src.constants.base import COLS_IDX, NET_LABEL
from src.funcs.emd import delta_k
from src.funcs.format import fmt_kpartition
from src.middlewares.profile import profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution

EXACT_K_LABEL: str = "ExactK"
EXACT_K_STRATEGY_TAG: str = f"{EXACT_K_LABEL}_strategy"


def _weak_k_partitions(elements: tuple[int, ...], k: int) -> Generator[tuple[tuple[int, ...], ...]]:
    """Yield every k-tuple of subsets that partitions ``elements`` allowing empty blocks.

    A weak k-partition is a list of ``k`` subsets that, taken together, are a
    partition of ``elements``. Empty subsets are allowed. Order matters: the
    same partition expressed as ``(A, B)`` versus ``(B, A)`` is yielded twice.

    The whole universe may land in a single slot (the rest being empty),
    which is the legacy ``sub_purview=∅`` or ``sub_mechanism=∅`` semantics.
    """
    if k < 1:
        return
    elements_tuple = tuple(sorted(elements))

    # Case 1: the universe lives in a single slot (e.g. legacy (∅, {0,1,2})).
    for slot in range(k):
        blocks: list[tuple[int, ...]] = [tuple() for _ in range(k)]
        blocks[slot] = elements_tuple
        yield tuple(blocks)

    # Case 2: the universe is split into r >= 2 non-empty blocks (r <= k).
    for r in range(2, min(k, len(elements_tuple)) + 1):
        for partition in set_partitions(elements_tuple, r):
            for assignment in product(range(k), repeat=r):
                if len(set(assignment)) != r:
                    continue
                placed: list[tuple[int, ...]] = [tuple() for _ in range(k)]
                for slot, block in zip(assignment, partition, strict=False):
                    placed[slot] = tuple(sorted(int(i) for i in block))
                yield tuple(placed)


class ExhaustiveK(SIA):
    """Exact k-partition strategy using weak Stirling partitions."""

    def __init__(self, tpm: np.ndarray, initial_state: str, k: int) -> None:
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(EXACT_K_STRATEGY_TAG)
        self.k = k
        self.best_partition: KPartition | None = None

    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Run exact search for the best k-partition under the current subsystem."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        future_universe = tuple(int(i) for i in self.sia_subsystem.ncube_indices.tolist())
        present_universe = tuple(int(i) for i in self.sia_subsystem.ncube_dims.tolist())

        if self.k < 2:
            raise ValueError("k must be >= 2.")

        baseline = self.sia_marginal_dists
        best_loss = np.inf
        best_distribution = np.array([], dtype=np.float32)

        for candidate in self._candidate_partitions(future_universe, present_universe):
            loss, partition_distribution = delta_k(
                self.sia_subsystem,
                candidate,
                baseline_distribution=baseline,
            )
            if loss < best_loss:
                best_loss = loss
                best_distribution = partition_distribution
                self.best_partition = candidate
                if loss == 0.0:
                    break

        if self.best_partition is None:
            raise RuntimeError("ExactK failed to generate any valid k-partition candidate.")

        return Solution(
            strategy=f"{EXACT_K_LABEL}(k={self.k})",
            loss=float(best_loss),
            subsystem_distribution=baseline,
            partition_distribution=best_distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(self.best_partition.signature),
        )

    def _candidate_partitions(
        self,
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
    ) -> Generator[KPartition]:
        """Yield every unique valid k-partition candidate.

        Generates weak k-partitions for each dimension, then pairs them across
        all permutations. The resulting KPartition is validated; invalid or
        duplicate candidates are skipped.
        """
        seen_signatures: set[tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]] = set()

        future_options = list(_weak_k_partitions(future_universe, self.k))
        present_options = list(_weak_k_partitions(present_universe, self.k))

        for future_blocks in future_options:
            for present_blocks in present_options:
                for perm in permutations(range(self.k)):
                    blocks: list[tuple[tuple[int, ...], tuple[int, ...]]] = [
                        (tuple(future_blocks[idx]), tuple(present_blocks[perm[idx]]))
                        for idx in range(self.k)
                    ]
                    try:
                        candidate = KPartition.from_blocks(
                            blocks=blocks,
                            future_universe=future_universe,
                            present_universe=present_universe,
                        )
                    except ValueError:
                        # Rejects vacuous blocks and non-covering/universe mismatches.
                        continue
                    if candidate.signature in seen_signatures:
                        continue
                    seen_signatures.add(candidate.signature)
                    yield candidate
