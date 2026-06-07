import time

import numpy as np

from src.constants.base import ACTUAL, COLS_IDX, EFECTO, NET_LABEL, TYPE_TAG
from src.funcs.emd import effect_emd
from src.funcs.format import fmt_bipartition_q
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.solution import Solution

GEOMETRIC_LABEL: str = "Geometric"
GEOMETRIC_STRATEGY_TAG: str = f"{GEOMETRIC_LABEL}_strategy"
GEOMETRIC_ANALYSIS_TAG: str = f"{GEOMETRIC_LABEL}_analysis"


class GeometricSIA(SIA):
    """
    GeoMIP strategy - Method 2 (Dynamic Programming).

    Builds a transition table using Hamming distances between states to
    identify optimal bipartition candidates without exhaustively evaluating
    every combination.
    """

    def __init__(self, tpm: np.ndarray, initial_state: str):
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(GEOMETRIC_STRATEGY_TAG)
        self.transition_table: dict = {}
        self.vertices: set[tuple]
        self.partition_memo: dict[tuple, tuple[float, np.ndarray]] = {}

    @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def apply_strategy(
        self, condition: str, purview: str, mechanism: str
    ) -> Solution:
        self.sia_prepare_subsystem(condition, purview, mechanism)

        future = tuple((EFECTO, idx) for idx in self.sia_subsystem.ncube_indices)
        present = tuple((ACTUAL, idx) for idx in self.sia_subsystem.ncube_dims)

        self._flat_data = [cube.data.ravel() for cube in self.sia_subsystem.ncubes]

        self.vertices = set(present + future)
        dims = self.sia_subsystem.ncube_dims
        self.state_start = self.sia_subsystem.initial_state[dims]
        self.state_end = 1 - self.state_start

        mip = self.find_mip()
        fmt_mip = fmt_bipartition_q(list(mip), self.nodes_complement(mip))

        return Solution(
            strategy=GEOMETRIC_LABEL,
            loss=self.partition_memo[mip][0],
            subsystem_distribution=self.sia_marginal_dists,
            partition_distribution=self.partition_memo[mip][1],
            total_time=time.time() - self.sia_start_time,
            partition=fmt_mip,
        )

    def nodes_complement(self, nodes) -> list:
        return list(set(self.vertices) - set(nodes))

    def find_mip(self) -> tuple:
        """Find the lowest-loss bipartition using the transition table."""
        self.sia_logger.critic("Iniciando búsqueda geométrica.")
        n_vars = len(self.sia_subsystem.ncube_indices)
        self.ncube_idx = list(range(n_vars))
        self.paths: dict[int, list[list[int]]] = {0: [self.state_start.tolist()]}

        for level in range(1, len(self.state_start) + 1):
            self._compute_level(self.state_end, level)

        candidates = self._identify_candidates()
        for present_sel, future_sel in candidates:
            present = self.sia_subsystem.ncube_dims[present_sel]
            effects = self.sia_subsystem.ncube_indices[future_sel]
            dist = self.sia_subsystem.bipartition(effects, present).marginal_distribution()
            emd = effect_emd(dist, self.sia_marginal_dists)
            key = [(ACTUAL, x) for x in present] + [(EFECTO, x) for x in effects]
            self.partition_memo[tuple(key)] = (emd, dist)

        return min(self.partition_memo, key=lambda k: self.partition_memo[k][0])

    def _compute_level(self, state_final: np.ndarray, level: int) -> None:
        visited: set[tuple] = set()
        self.paths[level] = []
        for prev_state in self.paths[level - 1]:
            current = np.array(prev_state)
            for i in range(len(current)):
                if current[i] != state_final[i]:
                    new_state = current.copy()
                    new_state[i] = state_final[i]
                    tup = tuple(new_state)
                    if tup not in visited:
                        self.paths[level].append(new_state.tolist())
                        self._compute_cost(self.paths[0][0], new_state.tolist())
                        visited.add(tup)

    def _compute_cost(self, state_start: list, state_end: list) -> None:
        key = tuple(state_start), tuple(state_end)
        if key not in self.transition_table:
            self.transition_table[key] = [None] * len(self.ncube_idx)

        dh = self._hamming(state_start, state_end)
        factor = 1 / (2 ** dh)

        start_int = int("".join(map(str, state_start[::-1])), 2)
        end_int = int("".join(map(str, state_end[::-1])), 2)
        diffs = np.abs(
            np.array([f[start_int] for f in self._flat_data])
            - np.array([f[end_int] for f in self._flat_data])
        )
        self.transition_table[key] = diffs.tolist()

        # For multi-bit jumps, accumulate the single-bit neighbor costs.
        if dh > 1:
            for i in range(len(state_start)):
                if state_start[i] != state_end[i]:
                    neighbor = list(state_end)
                    neighbor[i] = state_start[i]
                    temp_key = tuple(state_start), tuple(neighbor)
                    self.transition_table[key] = [
                        self.transition_table[key][x] + self.transition_table[temp_key][x]
                        for x in self.ncube_idx
                    ]

        self.transition_table[key] = [factor * v for v in self.transition_table[key]]

    def _identify_candidates(self) -> list:
        key = tuple(self.paths[0][0]), tuple(self.state_end)
        costs = self.transition_table[key]
        n_vars = len(costs)

        candidates = [
            [[i for i in range(len(self.state_end))], [i for i in range(n_vars) if i != idx]]
            for idx in range(n_vars)
        ]

        half = (len(self.paths) // 2) + (1 if len(self.paths) % 2 else 0)
        for level in range(1, half):
            best_cost = 1e5
            present_level, effects_level = [], []
            for state in self.paths[level]:
                cost = 0
                present, effects = [], []
                current = self.transition_table[(tuple(self.paths[0][0]), tuple(state))]
                complement_state = (1 - np.array(state)).tolist()
                comp = self.transition_table[
                    (tuple(self.paths[0][0]), tuple(complement_state))
                ]
                for idx, bit in enumerate(state):
                    if bit == self.paths[0][0][idx]:
                        present.append(idx)
                for idx in self.ncube_idx:
                    if current[idx] <= comp[idx]:
                        effects.append(idx)
                        cost += current[idx]
                    else:
                        cost += comp[idx]
                if cost < best_cost:
                    best_cost = cost
                    present_level = present
                    effects_level = effects
            candidates.append([present_level, effects_level])

        return candidates

    def _hamming(self, a: list, b: list) -> int:
        return sum(x != y for x, y in zip(a, b, strict=False))
