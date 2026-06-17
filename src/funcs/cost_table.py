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
        flat_data: list[NDArray[np.float32]] | NDArray[np.float32],
        state_start: NDArray[np.int8],
        state_end: NDArray[np.int8],
    ) -> None:
        """Stack the per-node rows and precompute the powers of two, then build."""
        self.state_start = state_start
        self.state_end = state_end
        self._num_dims = int(state_start.size)
        self._powers = 1 << np.arange(self._num_dims, dtype=np.int64)
        self._origin = int(np.dot(state_start.astype(np.int64), self._powers))
        stacked = np.asarray(flat_data)
        self.num_nodes = stacked.shape[0]
        self.table: NDArray[np.float32] = self._build(stacked)

    def _build(self, stacked: np.ndarray) -> NDArray[np.float32]:
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
        origin_values = stacked[:, self._origin].astype(np.float32)
        table = np.empty((size, self.num_nodes), dtype=np.float32)
        table[self._origin] = np.float32(0.0)

        for level in range(1, num_dims + 1):
            level_states = order[boundaries[level] : boundaries[level + 1]]
            factor = np.float32(1.0 / (1 << level))
            for begin in range(0, level_states.size, COST_TABLE_CHUNK_ROWS):
                chunk = level_states[begin : begin + COST_TABLE_CHUNK_ROWS]
                acc = np.abs(stacked[:, chunk].T.astype(np.float32) - origin_values)
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
        """Return the per-node cost vector for the start -> end transition."""
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


def stack_node_values(subsystem) -> np.ndarray:
    """Return the (num_nodes, 2^m) node-value matrix for the subsystem, copied
    into one contiguous buffer preserving the cubes' dtype (an integer TPM stays
    compact; the cost table casts to float32 per chunk).
    """
    ncubes = subsystem.ncubes
    if not ncubes:
        return np.empty((0, 0), dtype=np.float32)
    size = ncubes[0].data.size
    stacked = np.empty((len(ncubes), size), dtype=ncubes[0].data.dtype)
    for row, cube in enumerate(ncubes):
        stacked[row] = cube.data.reshape(-1)
    return stacked


def _popcount(values: NDArray[np.int64], num_bits: int) -> NDArray[np.uint8]:
    """Per-element population count of (num_bits)-bit non-negative integers."""
    mask = (np.int64(1) << num_bits) - np.int64(1)
    return np.bitwise_count((values & mask).astype(np.uint64)).astype(np.uint8)


def _bit_reverse(values: NDArray[np.int64], num_bits: int) -> NDArray[np.int64]:
    """Reverse the lowest (num_bits) bits of each element."""
    reversed_values = np.zeros(values.shape, dtype=np.int64)
    for bit_pos in range(num_bits):
        reversed_values |= ((values >> bit_pos) & 1) << (num_bits - 1 - bit_pos)
    return reversed_values
