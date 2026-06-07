import time
from collections.abc import Callable

import numpy as np
import pandas as pd
from colorama import Fore

from src.constants.base import (
    ACTUAL,
    COLS_IDX,
    EFECTO,
    EXCEL_EXTENSION,
    FLOAT_ZERO,
    NET_LABEL,
    TYPE_TAG,
)
from src.constants.tags import DUMMY_ARR, DUMMY_EMD, ERROR_PARTITION
from src.funcs.emd import select_emd
from src.funcs.format import fmt_bipartition
from src.funcs.labels import literals
from src.funcs.partitions import (
    bipartitions,
    generate_candidates,
    generate_partitions,
    generate_subsystems,
)
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.models.core.system import System

BRUTEFORCE_LABEL: str = "BruteForce"
BRUTEFORCE_STRATEGY_TAG: str = f"{BRUTEFORCE_LABEL}_strategy"
BRUTEFORCE_ANALYSIS_TAG: str = f"{BRUTEFORCE_LABEL}_analysis"
BRUTEFORCE_FULL_ANALYSIS_TAG: str = f"{BRUTEFORCE_LABEL}_full_analysis"


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

    @profile(context={TYPE_TAG: BRUTEFORCE_FULL_ANALYSIS_TAG})
    def analyze_full_network(self, output_dir) -> None:
        """
        Exhaustive network analysis: generates every candidate system,
        subsystem and bipartition, saving the results to Excel.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        state_dims = np.array([int(b) for b in self.initial_state], dtype=np.int8)
        system = System(self.tpm, state_dims)
        count = len(self.initial_state)

        for dims in generate_candidates(count):
            candidate = system.condition(np.array(dims, dtype=np.int8))
            name = literals(np.setdiff1d(candidate.ncube_dims, np.array(dims, dtype=np.int8)))
            results_file = output_dir / f"{name}.{EXCEL_EXTENSION}"

            with pd.ExcelWriter(results_file) as writer:
                for purv_rem, mech_rem in generate_subsystems(candidate.ncube_dims):
                    if len(purv_rem) == candidate.ncube_indices.size:
                        continue
                    subsystem = candidate.subtract(
                        np.array(purv_rem, dtype=np.int8),
                        np.array(mech_rem, dtype=np.int8),
                    )
                    dist = subsystem.marginal_distribution()
                    m = subsystem.ncube_indices.size
                    n = subsystem.ncube_dims.size

                    results = pd.DataFrame(
                        columns=[f"{i:0{m}b}" for i in range(1 << (m - 1))],
                        index=[f"{i:0{n}b}" for i in range(1 << n)],
                        dtype=np.float32,
                    )
                    for purv_bits, mech_bits in generate_partitions(m, n):
                        sub_purv = np.array([i for i, b in enumerate(purv_bits) if b], dtype=np.int8)
                        sub_mech = np.array([i for i, b in enumerate(mech_bits) if b], dtype=np.int8)
                        part = subsystem.bipartition(sub_purv, sub_mech)
                        emd_val = self.distance_metric(part.marginal_distribution(), dist)
                        results.loc[
                            "".join(map(str, mech_bits.astype(int))),
                            "".join(map(str, purv_bits.astype(int))),
                        ] = emd_val

                    eff_rem = np.setdiff1d(candidate.ncube_dims, np.array(purv_rem, dtype=np.int8))
                    cause_rem = np.setdiff1d(candidate.ncube_dims, np.array(mech_rem, dtype=np.int8))
                    sheet = f"{literals(eff_rem)}|{literals(cause_rem)}"
                    results.to_excel(writer, sheet_name=sheet)

        print(f"{Fore.GREEN}Análisis completo. Revisa review/resolver/")
