"""KGeoMIP — geometric strategy extended to k-partitions.

This strategy generalizes GeoMIP (the geometric/dynamic-programming bipartition
method) to k-partitions with k ∈ {2..5}, following the official specification

starting from the whole subsystem as a single block, it repeatedly
splits one block with the geometric bipartition method, until k blocks are obtained.
The reusable transition-cost table is built once from the original subsystem and
used for every candidate bipartition during the refinement process.
"""

import time

import numpy as np

from src.constants.base import COLS_IDX, NET_LABEL, TYPE_TAG
from src.constants.strategies import KGEOMIP_ANALYSIS_TAG, KGEOMIP_LABEL, KGEOMIP_STRATEGY_TAG
from src.funcs.cost_table import CostTable
from src.funcs.format import fmt_kpartition
from src.funcs.k_refine import Block, greedy_k_partition
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution


class KGeoMIP(SIA):
    """Geometric k-partition strategy reusing the cost table T."""

    def __init__(self, tpm: np.ndarray, initial_state: str, k: int) -> None:
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(KGEOMIP_STRATEGY_TAG)
        self.k = k
        self.cost_table: CostTable
        self.best_partition: KPartition | None = None

    @profile(context={TYPE_TAG: KGEOMIP_ANALYSIS_TAG})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Search for a low-loss k-partition under the current subsystem."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        if self.k < 2:
            raise ValueError("k must be >= 2.")

        subsystem = self.sia_subsystem
        baseline = self.sia_marginal_dists

        future_universe = tuple(int(i) for i in subsystem.ncube_indices.tolist())
        present_universe = tuple(int(i) for i in subsystem.ncube_dims.tolist())

        self.cost_table = self._build_cost_table(subsystem)
        cut_pool = self._cut_pool(subsystem)

        self.sia_logger.critic("Iniciando búsqueda geométrica k-partita.")
        partition, loss, distribution = greedy_k_partition(
            subsystem, baseline, cut_pool, future_universe, present_universe, self.k
        )
        self.best_partition = partition

        return Solution(
            strategy=f"{KGEOMIP_LABEL}(k={self.k})",
            loss=loss,
            subsystem_distribution=baseline,
            partition_distribution=distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(partition.signature),
        )

    def _build_cost_table(self, subsystem) -> CostTable:
        """Construct the reusable Hamming-weighted transition-cost table T."""
        flat_data = [cube.data.ravel() for cube in subsystem.ncubes]
        state_start = subsystem.initial_state[subsystem.ncube_dims]
        state_end = 1 - state_start

        return CostTable(flat_data, state_start, state_end)

    def _cut_pool(self, subsystem) -> list[Block]:
        """
        Map the cost table's bipartition candidates to actual-index blocks.

        Each geometric candidate [present_positions, future_positions] is
        converted into the block (future_indices, present_indices) it
        selects, so it can be intersected with any sub-block during refinement.
        """
        dims = subsystem.ncube_dims
        indices = subsystem.ncube_indices
        pool: list[Block] = []

        for present_pos, future_pos in self.cost_table.candidate_bipartitions():
            effect_set = frozenset(int(x) for x in indices[future_pos])
            present_set = frozenset(int(x) for x in dims[present_pos])
            pool.append((effect_set, present_set))

        return pool
