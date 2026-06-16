"""Legacy dict-of-tuples cost table, kept only for regression testing."""

import numpy as np
from numpy.typing import NDArray


class LegacyCostTable:
    """Original dict-of-tuples cost table implementation,
    kept for reference and testing against the new array-based version.
    """

    def __init__(
        self,
        flat_data: list[NDArray[np.float32]],
        state_start: NDArray[np.int8],
        state_end: NDArray[np.int8],
    ) -> None:
        """Stack the per-node rows and precompute the powers of two, then build."""
        self._flat = np.ascontiguousarray(np.stack(flat_data))
        self.state_start = state_start
        self.state_end = state_end
        self.num_nodes = len(flat_data)
        self._powers = 1 << np.arange(state_start.size, dtype=np.int64)
        self.transition_table: dict[tuple, NDArray[np.float64]] = {}
        self.paths: dict[int, list[list[int]]] = {}
        self._build()

    def _build(self) -> None:
        """Populate :attr:paths and :attr:transition_table level by level."""
        self.paths = {0: [self.state_start.tolist()]}
        for level in range(1, len(self.state_start) + 1):
            self._compute_level(level)

    def _compute_level(self, level: int) -> None:
        """Expand every vertex at the previous level by flipping one bit towards the end state,
        then compute the cost of the transition from the initial state to the new vertex, using the
        costs of single-bit neighbors if the Hamming distance is greater than 1.
        """
        visited: set[tuple] = set()
        self.paths[level] = []
        for prev_state in self.paths[level - 1]:
            current = np.array(prev_state)
            for k, _ in enumerate(current):
                if current[k] != self.state_end[k]:
                    new_state = current.copy()
                    new_state[k] = self.state_end[k]
                    tup = tuple(new_state)
                    if tup not in visited:
                        self.paths[level].append(new_state.tolist())
                        self._compute_cost(self.paths[0][0], new_state.tolist())
                        visited.add(tup)

    def _compute_cost(self, state_start: list, state_end: list) -> None:
        """Compute the cost of the transition from (state_start) to (state_end) and
        store it in the table, using the costs of single-bit neighbors
        if the Hamming distance is greater than 1.
        """
        key = tuple(state_start), tuple(state_end)
        dh = self._hamming(state_start, state_end)
        factor = 1.0 / (2**dh)

        start_int = int(np.dot(state_start, self._powers))
        end_int = int(np.dot(state_end, self._powers))
        cost = np.abs(self._flat[:, start_int] - self._flat[:, end_int])

        if dh > 1:
            for k, _ in enumerate(state_start):
                if state_start[k] != state_end[k]:
                    neighbor = list(state_end)
                    neighbor[k] = state_start[k]
                    cost = (
                        cost
                        + self.transition_table[(tuple(state_start), tuple(neighbor))]
                    )

        self.transition_table[key] = factor * cost

    def cost(self, state_start: list, state_end: list) -> NDArray[np.float64]:
        """Return the per-node cost vector for the start -> end transition."""
        return self.transition_table[(tuple(state_start), tuple(state_end))]

    def candidate_bipartitions(self) -> list[list[list[int]]]:
        """Propose bipartition candidates from the cost table (legacy walk)."""
        paths = self.paths
        table = self.transition_table

        origin = paths[0][0]
        costs = table[(tuple(origin), tuple(self.state_end))]
        n_vars = len(costs)

        candidates: list[list[list[int]]] = [
            [
                list(range(len(self.state_end))),
                list(i for i in range(n_vars) if i != idx),
            ]
            for idx in range(n_vars)
        ]

        half = (len(paths) // 2) + (1 if len(paths) % 2 else 0)
        for level in range(1, half):
            best_cost = float("inf")
            present_level: list[int] = []
            effects_level: list[int] = []
            for state in paths[level]:
                cost = 0.0
                present, effects = [], []
                current = table[(tuple(origin), tuple(state))]
                complement_state = (1 - np.array(state)).tolist()
                comp = table[(tuple(origin), tuple(complement_state))]
                for idx, bit in enumerate(state):
                    if bit == origin[idx]:
                        present.append(idx)
                for idx in range(n_vars):
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

    @staticmethod
    def _hamming(a: list, b: list) -> int:
        """Hamming distance between two equal-length bit lists."""
        return sum(x != y for x, y in zip(a, b, strict=False))
