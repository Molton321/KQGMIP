"""
Cost table implementation for the transition from the initial state to all reachable states,
with methods to retrieve costs and propose bipartition candidates based on the table.
"""

import numpy as np
from numpy.typing import NDArray

from src.constants.strategies import COST_TABLE_CHUNK_ROWS


class CostTable:
    """Class for the transition cost table, mapping every reachable state from the
    initial state to the per-node cost vector of the transition from the initial state.
    """

    def __init__(
        self,
        flat_data: list[NDArray[np.float32]],
        state_start: NDArray[np.int8],
        state_end: NDArray[np.int8],
    ) -> None:
        """Stack the per-node rows and precompute the powers of two, then build."""
        self.state_start = state_start
        self.state_end = state_end
        self.num_nodes = len(flat_data)
        self._flats = [np.ascontiguousarray(flat) for flat in flat_data]
        self._num_dims = int(state_start.size)
        self._powers = 1 << np.arange(self._num_dims, dtype=np.int64)
        self._origin = int(np.dot(state_start.astype(np.int64), self._powers))
        self.table: NDArray[np.float32] = self._build()

    def _build(self) -> NDArray[np.float32]:
        """Populate the cost table level by level, flipping bits away from the origin
        and accumulating costs from single-bit neighbors. The table is stored as a
        2^m × num_nodes array, indexed by the integer representation of the state.
        """
        num_dims = self._num_dims
        size = 1 << num_dims
        states = np.arange(size, dtype=np.int64)
        self._dist = _popcount(states ^ self._origin, num_dims)
        dist = self._dist
        order = np.argsort(dist, kind="stable")
        boundaries = np.searchsorted(dist[order], np.arange(num_dims + 2))

        origin_values = np.array(
            [np.float32(flat[self._origin]) for flat in self._flats],
            dtype=np.float32,
        )

        table = np.empty((size, self.num_nodes), dtype=np.float32)
        table[self._origin] = np.float32(0.0)

        for level in range(1, num_dims + 1):
            level_states = order[boundaries[level] : boundaries[level + 1]]
            factor = np.float32(1.0 / (1 << level))
            for begin in range(0, level_states.size, COST_TABLE_CHUNK_ROWS):
                chunk = level_states[begin : begin + COST_TABLE_CHUNK_ROWS]
                acc = np.empty((chunk.size, self.num_nodes), dtype=np.float32)
                for node, flat in enumerate(self._flats):
                    acc[:, node] = np.abs(
                        flat[chunk].astype(np.float32, copy=False) - origin_values[node]
                    )
                if level > 1:
                    flipped = chunk ^ self._origin
                    for bit_pos in range(num_dims):
                        bit = 1 << bit_pos
                        selected = (flipped & bit) != 0
                        if selected.any():
                            acc[selected] += table[chunk[selected] ^ bit]
                table[chunk] = acc * factor
        return table

    def cost(self, state_start: list, state_end: list) -> NDArray[np.float32]:
        """Return the per-node cost vector for the ``start -> end`` transition."""
        if tuple(state_start) != tuple(self.state_start.tolist()):
            raise KeyError(
                "CostTable solo almacena transiciones desde el estado inicial "
                f"{self.state_start.tolist()}, no desde {list(state_start)}."
            )
        end_int = int(np.dot(np.asarray(state_end, dtype=np.int64), self._powers))
        return self.table[end_int]

    def candidate_bipartitions(self) -> list[list[list[int]]]:
        """Propose bipartition candidates from the cost table.
        The first candidates are the single-bit flips, then the states are processed level by level,
        starting from the closest to the origin, and the best bipartition is selected for each level.
        """
        num_dims = self._num_dims
        n_vars = self.num_nodes
        full_mask = (1 << num_dims) - 1

        candidates: list[list[list[int]]] = [
            [
                list(range(len(self.state_end))),
                list(i for i in range(n_vars) if i != idx),
            ]
            for idx in range(n_vars)
        ]

        num_levels = num_dims + 1
        half = (num_levels // 2) + (1 if num_levels % 2 else 0)
        states = np.arange(1 << num_dims, dtype=np.int64)
        dist = self._dist

        for level in range(1, half):
            level_states = states[dist == level]
            revs = _bit_reverse(level_states ^ self._origin, num_dims)
            level_states = level_states[np.argsort(revs, kind="stable")[::-1]]

            best_cost = np.inf
            best_state = int(level_states[0]) if level_states.size else self._origin
            for begin in range(0, level_states.size, COST_TABLE_CHUNK_ROWS):
                chunk = level_states[begin : begin + COST_TABLE_CHUNK_ROWS]
                current = self.table[chunk]
                complement = self.table[chunk ^ full_mask]
                chunk_costs = np.minimum(current, complement).sum(
                    axis=1, dtype=np.float64
                )
                pos = int(np.argmin(chunk_costs))
                if chunk_costs[pos] < best_cost:
                    best_cost = float(chunk_costs[pos])
                    best_state = int(chunk[pos])

            flipped = best_state ^ self._origin
            present_level = [idx for idx in range(num_dims) if not (flipped >> idx) & 1]
            current_row = self.table[best_state]
            complement_row = self.table[best_state ^ full_mask]
            effects_level = [
                idx for idx in range(n_vars) if current_row[idx] <= complement_row[idx]
            ]
            candidates.append([present_level, effects_level])

        return candidates


def _popcount(values: NDArray[np.int64], num_bits: int) -> NDArray[np.uint8]:
    """Per-element population count of (num_bits)-bit non-negative integers."""
    remaining = values.astype(np.uint64, copy=True)
    counts = np.zeros(values.shape, dtype=np.uint8)
    for _ in range(num_bits):
        counts += (remaining & np.uint64(1)).astype(np.uint8)
        remaining >>= np.uint64(1)
    return counts


def _bit_reverse(values: NDArray[np.int64], num_bits: int) -> NDArray[np.int64]:
    """Reverse the lowest (num_bits) bits of each element."""
    reversed_values = np.zeros(values.shape, dtype=np.int64)
    for bit_pos in range(num_bits):
        reversed_values |= ((values >> bit_pos) & 1) << (num_bits - 1 - bit_pos)
    return reversed_values


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
        """Populate :attr:`paths` and :attr:`transition_table` level by level."""
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
        """Return the per-node cost vector for the ``start -> end`` transition."""
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
            best_cost = 1e5
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
