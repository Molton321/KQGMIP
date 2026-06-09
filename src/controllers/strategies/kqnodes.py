"""KQNodes — submodular strategy extended to k-partitions.

This strategy generalizes QNodes (the Queyranne-like submodular bipartition
search) to k-partitions with k ∈ {2..5}.

KQNodes runs the submodular search once to obtain its pool of candidate
bipartitions (partition_memo), converts each candidate into a cut, and then
delegates to the shared greedy hierarchical engine to find a low-loss k-partition
refining those cuts.
"""

import time

import numpy as np

from src.constants.base import ACTUAL, EFECTO, TYPE_TAG
from src.constants.strategies import KQNODES_ANALYSIS_TAG, KQNODES_LABEL, KQNODES_STRATEGY_TAG
from src.controllers.strategies.q_nodes import QNodes
from src.funcs.format import fmt_kpartition
from src.funcs.k_refine import Block, greedy_k_partition
from src.middlewares.profile import profile
from src.middlewares.slogger import SafeLogger
from src.models.core.partition import KPartition
from src.models.core.solution import Solution


class KQNodes(QNodes):
    """Submodular k-partition strategy (k ∈ {2..5}) extending QNodes."""

    def __init__(self, tpm: np.ndarray, initial_state: str, k: int) -> None:
        super().__init__(tpm, initial_state)
        self.logger = SafeLogger(KQNODES_STRATEGY_TAG)
        self.k = k
        self.best_partition: KPartition | None = None

    @profile(context={TYPE_TAG: KQNODES_ANALYSIS_TAG})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Search for a low-loss k-partition using the submodular candidate pool."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        if self.k < 2:
            raise ValueError("k must be >= 2.")

        subsystem = self.sia_subsystem
        baseline = self.sia_marginal_dists

        future = tuple((EFECTO, effect) for effect in subsystem.ncube_indices)
        present = tuple((ACTUAL, current) for current in subsystem.ncube_dims)

        future_universe = tuple(int(i) for i in subsystem.ncube_indices.tolist())
        present_universe = tuple(int(i) for i in subsystem.ncube_dims.tolist())

        self.algorithm(list(present + future))
        cut_pool = self._cut_pool()

        self.sia_logger.critic("Iniciando búsqueda submodular k-partita.")
        partition, loss, distribution = greedy_k_partition(
            subsystem, baseline, cut_pool, future_universe, present_universe, self.k
        )
        self.best_partition = partition

        return Solution(
            strategy=f"{KQNODES_LABEL}(k={self.k})",
            loss=loss,
            subsystem_distribution=baseline,
            partition_distribution=distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(partition.signature),
        )

    def _cut_pool(self) -> list[Block]:
        """
        Convert the submodular candidate sides (memo keys) into cuts.
        Each (partition_memo) key represents one side of a candidate
        bipartition as a (possibly nested) collection of (time, index)
        vertices. The side is flattened and split by layer into a
        (future_indices, present_indices) cut for the refinement engine.
        """
        pool: list[Block] = []

        for key in self.partition_memo:
            vertices = self._flatten_vertices(key)
            effects = frozenset(index for time, index in vertices if time == EFECTO)
            present = frozenset(index for time, index in vertices if time == ACTUAL)
            pool.append((effects, present))

        return pool

    @classmethod
    def _flatten_vertices(cls, node) -> list[tuple[int, int]]:
        """
        Recursively flatten a memo key into (time, index) vertices.
        A vertex is a 2-tuple of integers (time, index); merged candidate
        groups are lists, so anything that is not a plain integer 2-tuple is
        recursed into.
        """
        if (
            isinstance(node, tuple)
            and len(node) == 2
            and all(isinstance(component, (int, np.integer)) for component in node)
        ):
            return [(int(node[0]), int(node[1]))]

        vertices: list[tuple[int, int]] = []

        for element in node:
            vertices.extend(cls._flatten_vertices(element))

        return vertices
