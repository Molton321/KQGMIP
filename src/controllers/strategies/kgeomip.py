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
from src.funcs.cost_table import CostTable, stack_node_values
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
        return self.apply_strategy_for_ks(condition, purview, mechanism, (self.k,))[
            self.k
        ]

    def apply_strategy_for_ks(
        self,
        condition: str,
        purview: str,
        mechanism: str,
        ks: tuple[int, ...],
    ) -> dict[int, Solution]:
        """Solve the same subsystem for several k values sharing the cost table.

        The cost table is computed once per system and reused for every k.
        This entry point realizes that for grid/batch runs: subsystem
        preparation, cost table and cut pool are built once, then each requested
        k runs only its greedy refinement. The reported per-k time charges the
        shared preparation to the first k and the refinement to each k, so the
        cell times add up to the real wall-clock cost.
        """
        ks = tuple(dict.fromkeys(ks))
        if not ks or min(ks) < 2:
            raise ValueError("k must be >= 2.")

        prep_begin = time.perf_counter()
        self.sia_prepare_subsystem(condition, purview, mechanism)

        subsystem = self.sia_subsystem
        baseline = self.sia_marginal_dists

        future_universe = tuple(int(i) for i in subsystem.ncube_indices.tolist())
        present_universe = tuple(int(i) for i in subsystem.ncube_dims.tolist())

        self.cost_table = self._build_cost_table(subsystem)
        cut_pool = self._cut_pool(subsystem)
        prep_seconds = time.perf_counter() - prep_begin

        self.sia_logger.critic("Iniciando búsqueda geométrica k-partita.")
        solutions: dict[int, Solution] = {}
        for position, k in enumerate(ks):
            refine_begin = time.perf_counter()
            partition, loss, distribution = greedy_k_partition(
                subsystem, baseline, cut_pool, future_universe, present_universe, k
            )
            elapsed = time.perf_counter() - refine_begin
            if position == 0:
                elapsed += prep_seconds
            self.best_partition = partition
            solutions[k] = Solution(
                strategy=f"{KGEOMIP_LABEL}(k={k})",
                loss=loss,
                subsystem_distribution=baseline,
                partition_distribution=distribution,
                total_time=elapsed,
                partition=fmt_kpartition(partition.signature),
            )
        return solutions

    def _build_cost_table(self, subsystem) -> CostTable:
        """Construct the reusable Hamming-weighted transition-cost table T."""
        stacked = stack_node_values(subsystem)
        state_start = subsystem.initial_state[subsystem.ncube_dims]
        state_end = 1 - state_start

        return CostTable(stacked, state_start, state_end)

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
