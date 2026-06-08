"""Reusable transition-cost table T for the geometric strategies.

The geometric method (GeoMIP, official doc ``docs/Proyecto_KQMIP.md`` §2.3 and
``docs/algoritmos.md`` §4) interprets the state space as an n-dimensional
hypercube and builds a *cost table* ``T`` of transitions between the initial
state and the rest of the vertices. Each entry encodes, per effect n-cube, the
energy/inertia of moving between two states, weighted by the Hamming distance:

    tx(start, end)[i] = γ · |X_i[start] - X_i[end]|,   γ = 1 / 2^{d_H(start, end)}

This table is the most expensive part of the geometric analysis. The official
specification (``§3``, line 103) requires it to be **computed once per system
and reused to evaluate every k-partition candidate, independently of k**. This
module isolates that computation so both ``GeometricSIA`` (k=2) and ``KGeoMIP``
(k∈{2..5}) consume the same table instead of recomputing it.
"""

import numpy as np
from numpy.typing import NDArray


class CostTable:
    """Hamming-weighted transition-cost table over the hypercube of states.

    The table is built with a breadth-first walk that flips, level by level,
    the bits separating the initial state ``state_start`` from its complement
    ``state_end``. For every reached vertex it stores a per-node cost vector
    (one entry per effect n-cube) in :attr:`transition_table`.

    Args:
        flat_data: One raveled probability array per effect n-cube. The array
            for node ``i`` is indexed by the little-endian integer of a
            mechanism substate, so ``flat_data[i][state_int]`` is the marginal
            probability contribution of node ``i`` at that state.
        state_start: Initial mechanism substate as a 0/1 array.
        state_end: Target substate (``1 - state_start``), the hypercube vertex
            antipodal to ``state_start``.

    Attributes:
        transition_table: Maps ``(start_tuple, end_tuple)`` to the per-node cost
            vector ``list[float]`` of length ``num_nodes``.
        paths: Maps a Hamming level to the list of vertices (as ``list[int]``)
            reachable from ``state_start`` at exactly that distance.
        num_nodes: Number of effect n-cubes (length of every cost vector).
    """

    def __init__(
        self,
        flat_data: list[NDArray[np.float32]],
        state_start: NDArray[np.int8],
        state_end: NDArray[np.int8],
    ) -> None:
        # Stack the per-node rows into a contiguous (num_nodes, 2^m) matrix so a
        # state's per-node values are a single vectorized column gather.
        self._flat = np.ascontiguousarray(np.stack(flat_data))
        self.state_start = state_start
        self.state_end = state_end
        self.num_nodes = len(flat_data)
        # Powers of two for the little-endian bit-list -> int conversion (avoids
        # the per-state ``int("".join(map(str, ...)), 2)`` string formatting).
        self._powers = (1 << np.arange(state_start.size, dtype=np.int64))
        self.transition_table: dict[tuple, NDArray[np.float64]] = {}
        self.paths: dict[int, list[list[int]]] = {}
        self._build()

    def _build(self) -> None:
        """Populate :attr:`paths` and :attr:`transition_table` level by level."""
        self.paths = {0: [self.state_start.tolist()]}
        for level in range(1, len(self.state_start) + 1):
            self._compute_level(level)

    def _compute_level(self, level: int) -> None:
        """Expand every vertex at ``level - 1`` toward ``state_end`` by one bit."""
        visited: set[tuple] = set()
        self.paths[level] = []
        for prev_state in self.paths[level - 1]:
            current = np.array(prev_state)
            for i in range(len(current)):
                if current[i] != self.state_end[i]:
                    new_state = current.copy()
                    new_state[i] = self.state_end[i]
                    tup = tuple(new_state)
                    if tup not in visited:
                        self.paths[level].append(new_state.tolist())
                        self._compute_cost(self.paths[0][0], new_state.tolist())
                        visited.add(tup)

    def _compute_cost(self, state_start: list, state_end: list) -> None:
        """Store the per-node transition cost vector for ``start -> end``.

        Single-bit jumps read the node-wise absolute difference directly; for
        multi-bit jumps the single-bit neighbor costs are accumulated, and the
        whole vector is finally scaled by ``γ = 1 / 2^{d_H}``.
        """
        key = tuple(state_start), tuple(state_end)
        dh = self._hamming(state_start, state_end)
        factor = 1.0 / (2 ** dh)

        # Little-endian bit list -> flat index via a dot with the powers of two.
        start_int = int(np.dot(state_start, self._powers))
        end_int = int(np.dot(state_end, self._powers))
        # Vectorized per-node absolute difference (single column gather + abs).
        cost = np.abs(self._flat[:, start_int] - self._flat[:, end_int])

        # For multi-bit jumps, accumulate the single-bit neighbor costs.
        if dh > 1:
            for i in range(len(state_start)):
                if state_start[i] != state_end[i]:
                    neighbor = list(state_end)
                    neighbor[i] = state_start[i]
                    cost = cost + self.transition_table[(tuple(state_start), tuple(neighbor))]

        self.transition_table[key] = factor * cost

    def cost(self, state_start: list, state_end: list) -> NDArray[np.float64]:
        """Return the per-node cost vector for the ``start -> end`` transition."""
        return self.transition_table[(tuple(state_start), tuple(state_end))]

    def candidate_bipartitions(self) -> list[list[list[int]]]:
        """Propose bipartition candidates from the cost table.

        Returns a list of ``[present_positions, future_positions]`` selections,
        where ``present_positions`` index into the mechanism dimensions and
        ``future_positions`` index into the effect n-cubes. The pool combines:

        - the ``n`` single-node cuts (each effect node isolated), and
        - for every Hamming level up to the midpoint, the lowest-cost
          assignment of each node to the start side or its complement.

        This is the geometric candidate set shared by ``GeometricSIA`` (k=2,
        which scores each candidate with EMD) and ``KGeoMIP`` (k≥2, which
        projects these cuts onto sub-blocks for hierarchical refinement).
        """
        paths = self.paths
        table = self.transition_table

        origin = paths[0][0]
        costs = table[(tuple(origin), tuple(self.state_end))]
        n_vars = len(costs)

        candidates: list[list[list[int]]] = [
            [[i for i in range(len(self.state_end))], [i for i in range(n_vars) if i != idx]]
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
        return sum(x != y for x, y in zip(a, b, strict=False))
