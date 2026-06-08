import time
from collections.abc import Callable

import numpy as np

from src.constants.base import (
    ACTUAL,
    COLS_IDX,
    EFECTO,
    FLOAT_ZERO,
    NET_LABEL,
)
from src.constants.tags import DUMMY_ARR, DUMMY_EMD, ERROR_PARTITION
from src.funcs.emd import select_emd
from src.funcs.format import fmt_bipartition
from src.funcs.partitions import (
    bipartitions,
)
from src.middlewares.profile import profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.solution import Solution

BRUTEFORCE_LABEL: str = "BruteForce"
BRUTEFORCE_STRATEGY_TAG: str = f"{BRUTEFORCE_LABEL}_strategy"
BRUTEFORCE_ANALYSIS_TAG: str = f"{BRUTEFORCE_LABEL}_analysis"


class BruteForce(SIA):
    """
    Brute-force strategy: evaluates every possible bipartition and selects the
    one that minimizes the EMD against the original subsystem.

    Complexity: O(2^(m+n)) where m = |purview|, n = |mechanism|.
    """

    def __init__(self, tpm: np.ndarray, initial_state: str):
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.distance_metric: Callable = select_emd()
        self.logger = SafeLogger(BRUTEFORCE_STRATEGY_TAG)

    def apply_strategy(
        self, condition: str, purview: str, mechanism: str
    ) -> Solution:
        self.sia_prepare_subsystem(condition, purview, mechanism)

        solution = Solution(
            BRUTEFORCE_LABEL,
            DUMMY_EMD,
            self.sia_marginal_dists,
            DUMMY_ARR,
            ERROR_PARTITION,
        )

        small_phi = np.inf
        best_dist: np.ndarray = DUMMY_ARR

        effects = self.sia_subsystem.ncube_indices
        causes = self.sia_subsystem.ncube_dims
        m, n = effects.size, causes.size

        for sub_purview, sub_mechanism in bipartitions(effects, causes, (1 << m) * (1 << n)):
            purview_arr = np.array(sub_purview, dtype=np.int8)
            mechanism_arr = np.array(sub_mechanism, dtype=np.int8)

            partition = self.sia_subsystem.bipartition(purview_arr, mechanism_arr)
            part_dist = partition.marginal_distribution()
            emd_val = self.distance_metric(part_dist, self.sia_marginal_dists)

            if emd_val < small_phi:
                small_phi = emd_val
                best_dist = part_dist
                bipart_prim = sub_mechanism, sub_purview
                bipart_dual = (
                    np.setdiff1d(causes, sub_mechanism),
                    np.setdiff1d(effects, sub_purview),
                )
                if emd_val == FLOAT_ZERO:
                    solution.loss = emd_val
                    solution.partition_distribution = part_dist
                    solution.partition = fmt_bipartition(
                        [bipart_prim[ACTUAL], bipart_prim[EFECTO]],
                        [bipart_dual[ACTUAL], bipart_dual[EFECTO]],
                    )
                    solution.execution_time = time.time() - self.sia_start_time
                    return solution

        solution.loss = small_phi
        solution.partition_distribution = best_dist
        solution.partition = fmt_bipartition(
            [bipart_prim[ACTUAL], bipart_prim[EFECTO]],
            [bipart_dual[ACTUAL], bipart_dual[EFECTO]],
        )
        solution.execution_time = time.time() - self.sia_start_time
        return solution
