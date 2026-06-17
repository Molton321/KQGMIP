"""
Geometric SIA strategy that uses a reusable transition-cost table built
from the Hamming distances between states to identify optimal bipartition
candidates without exhaustively evaluating every combination.
"""

import time

import numpy as np

from src.constants.base import ACTUAL, COLS_IDX, EFECTO, NET_LABEL, TYPE_TAG
from src.constants.strategies import GEOMETRIC_ANALYSIS_TAG, GEOMETRIC_LABEL, GEOMETRIC_STRATEGY_TAG
from src.funcs.cost_table import CostTable, stack_node_values
from src.funcs.emd import effect_emd
from src.funcs.format import fmt_bipartition_q
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.solution import Solution


class GeometricSIA(SIA):
    """
    Geometric strategy: uses the transition table to find the bipartition
    that minimizes the EMD against the original subsystem.
    """

    def __init__(self, tpm: np.ndarray, initial_state: str):
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(GEOMETRIC_STRATEGY_TAG)
        self.cost_table: CostTable
        self.vertices: set[tuple]
        self.state_start: np.ndarray
        self.state_end: np.ndarray
        self.partition_memo: dict[tuple, tuple[float, np.ndarray]] = {}

    @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Use the transition table to find the bipartition that minimizes the EMD."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        future = tuple((EFECTO, idx) for idx in self.sia_subsystem.ncube_indices)
        present = tuple((ACTUAL, idx) for idx in self.sia_subsystem.ncube_dims)
        stacked = stack_node_values(self.sia_subsystem)

        self.vertices = set(present + future)
        dims = self.sia_subsystem.ncube_dims
        self.state_start = self.sia_subsystem.initial_state[dims]
        self.state_end = 1 - self.state_start
        self.cost_table = CostTable(stacked, self.state_start, self.state_end)

        mip = self.find_mip()
        fmt_mip = fmt_bipartition_q(list(mip), self.nodes_complement(mip))

        return Solution(
            strategy=GEOMETRIC_LABEL,
            loss=self.partition_memo[mip][0],
            subsystem_distribution=self.sia_marginal_dists,
            partition_distribution=self.partition_memo[mip][1],
            total_time=time.perf_counter() - self.sia_start_time,
            partition=fmt_mip,
        )

    def nodes_complement(self, nodes) -> list:
        return list(set(self.vertices) - set(nodes))

    def find_mip(self) -> tuple:
        """Find the lowest-loss bipartition using the transition table."""
        self.sia_logger.critic("Iniciando búsqueda geométrica.")

        candidates = self.cost_table.candidate_bipartitions()
        for present_sel, future_sel in candidates:
            present = self.sia_subsystem.ncube_dims[present_sel]
            effects = self.sia_subsystem.ncube_indices[future_sel]
            dist = self.sia_subsystem.bipartition(
                effects, present
            ).marginal_distribution()
            emd = effect_emd(dist, self.sia_marginal_dists)
            key = [(ACTUAL, x) for x in present] + [(EFECTO, x) for x in effects]
            self.partition_memo[tuple(key)] = (emd, dist)

        return min(self.partition_memo, key=lambda k: self.partition_memo[k][0])
