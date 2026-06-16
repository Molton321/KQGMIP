"""
QNodes strategy implementation. This strategy is based on the Q-Nodes algorithm,
which is a submodular optimization technique for finding low-loss bipartitions
in the context of SIA. The algorithm operates in phases, where in each phase it
iteratively builds a candidate partition by adding nodes that minimize the EMD gain.
The final output is the partition with the lowest global EMD against
the original subsystem distribution.
"""

import time

import numpy as np

from src.constants.base import ACTUAL, COLS_IDX, EFECTO, INFTY_POS, LAST_IDX, NET_LABEL, TYPE_TAG
from src.constants.strategies import QNODES_ANALYSIS_TAG, QNODES_LABEL, QNODES_STRATEGY_TAG
from src.funcs.emd import effect_emd
from src.funcs.format import fmt_bipartition_q
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.solution import Solution


class QNodes(SIA):
    """
    Q-Nodes strategy: greedy submodular (Queyranne-like) algorithm to search the MIP.
    Incrementally grows node groups while minimizing the information loss (effect EMD).
    """

    def __init__(self, tpm: np.ndarray, initial_state: str):
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.vertices: set[tuple]
        self.partition_memo: dict = {}
        self.logger = SafeLogger(QNODES_STRATEGY_TAG)

    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        self.sia_prepare_subsystem(condition, purview, mechanism)

        future = tuple((EFECTO, effect) for effect in self.sia_subsystem.ncube_indices)
        present = tuple((ACTUAL, current) for current in self.sia_subsystem.ncube_dims)

        self.vertices = set(present + future)
        mip = self.algorithm(list(present + future))

        fmt_mip = fmt_bipartition_q(list(mip), self.nodes_complement(mip))

        return Solution(
            strategy=QNODES_LABEL,
            loss=self.partition_memo[mip][0],
            subsystem_distribution=self.sia_marginal_dists,
            partition_distribution=self.partition_memo[mip][1],
            total_time=time.perf_counter() - self.sia_start_time,
            partition=fmt_mip,
        )

    @profile(context={TYPE_TAG: QNODES_ANALYSIS_TAG})
    def algorithm(self, vertices: list[tuple[int, int]]) -> tuple:
        """
        Algorithm Q: operates in phases (i) > cycles (j) > iterations (k).
        Omega starts with the first vertex and grows by adding, in each cycle, the
        delta with the smallest submodular gain. When each phase closes, a candidate
        pair is formed and memoized. Returns the key of the partition with the lowest
        global EMD.

        A subsystem of two or fewer vertices cannot enter the phase loop (which
        needs at least three vertices to form omega/delta cycles), so every
        singleton side is evaluated directly to populate partition_memo for
        the downstream cut pool.
        """
        phase_vertices = vertices

        if len(phase_vertices) <= 2:
            for i, v in enumerate(phase_vertices):
                side = (v,)
                complement = [other for j, other in enumerate(phase_vertices) if j != i]
                _, emd, dist = self.submodular_function(v, complement)
                self.partition_memo[side] = (emd, dist)
            return min(self.partition_memo, key=lambda k: self.partition_memo[k][0])

        for _ in range(len(phase_vertices) - 2):
            cycle_omegas = [phase_vertices[0]]
            cycle_deltas = phase_vertices[1:]

            candidate_partition_emd = INFTY_POS
            candidate_partition_dist = None

            for _ in range(len(cycle_deltas) - 1):
                local_emd = float("inf")
                mip_index = 0

                for k, v in enumerate(cycle_deltas):
                    union_emd, delta_emd, delta_marginal_dist = (
                        self.submodular_function(v, cycle_omegas)
                    )
                    iteration_emd = union_emd - delta_emd

                    if iteration_emd < local_emd:
                        local_emd = iteration_emd
                        mip_index = k

                    candidate_partition_emd = delta_emd
                    candidate_partition_dist = delta_marginal_dist

                cycle_omegas.append(cycle_deltas[mip_index])
                cycle_deltas.pop(mip_index)

            self.partition_memo[
                tuple(
                    cycle_deltas[LAST_IDX]
                    if isinstance(cycle_deltas[LAST_IDX], list)
                    else cycle_deltas
                )
            ] = (candidate_partition_emd, candidate_partition_dist)

            candidate_pair = (  # type: ignore[operator]
                [cycle_omegas[LAST_IDX]]
                if isinstance(cycle_omegas[LAST_IDX], tuple)
                else cycle_omegas[LAST_IDX]
            ) + (
                cycle_deltas[LAST_IDX]
                if isinstance(cycle_deltas[LAST_IDX], list)
                else cycle_deltas
            )

            cycle_omegas.pop()
            cycle_omegas.append(candidate_pair)  # type: ignore[arg-type]
            phase_vertices = cycle_omegas

        return min(self.partition_memo, key=lambda k: self.partition_memo[k][0])

    def submodular_function(
        self,
        deltas: tuple | list[tuple],
        omegas: list,
    ) -> tuple[float, float, np.ndarray]:
        """
        Evaluate the individual delta and its union with omega.
        Rebuilds the temporal state on every call (no shared state) to avoid the
        previous implementation's defect. Returns
        (union_emd, delta_emd, delta_marginal_dist).

        Both bipartitions are scored with the local marginal distribution
        (System.bipartition_marginal_distribution) instead of the full
        marginalized tensors; the values are identical.
        """
        temporal: list[list[int]] = [[], []]

        if isinstance(deltas, tuple):
            d_time, d_index = deltas
            temporal[d_time].append(d_index)
        else:
            for delta in deltas:
                d_time, d_index = delta
                temporal[d_time].append(d_index)

        delta_marginal_vector = self.sia_subsystem.bipartition_marginal_distribution(
            np.array(temporal[EFECTO], dtype=np.int8),
            np.array(temporal[ACTUAL], dtype=np.int8),
        )
        delta_emd = effect_emd(delta_marginal_vector, self.sia_marginal_dists)

        for omega in omegas:
            if isinstance(omega, list):
                for omg in omega:
                    o_time, o_index = omg
                    temporal[o_time].append(o_index)
            else:
                o_time, o_index = omega
                temporal[o_time].append(o_index)

        union_marginal_vector = self.sia_subsystem.bipartition_marginal_distribution(
            np.array(temporal[EFECTO], dtype=np.int8),
            np.array(temporal[ACTUAL], dtype=np.int8),
        )
        union_emd = effect_emd(union_marginal_vector, self.sia_marginal_dists)

        return union_emd, delta_emd, delta_marginal_vector

    def nodes_complement(self, nodes) -> list:
        return list(set(self.vertices) - set(nodes))
