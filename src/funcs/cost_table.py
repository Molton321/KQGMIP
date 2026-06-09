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

Two implementations live here:

- :class:`CostTable` — the production, **level-by-level vectorized** table
  (FASE 11). It stores the whole table as one ``(2^m, num_nodes)`` ``float32``
  array indexed by the little-endian integer of each state, and fills it with
  the same Hamming-level dynamic program as the legacy version but using NumPy
  gathers instead of Python dict/tuple bookkeeping. At m=25 this is ~3.36 GB
  and builds in minutes, where the dict-based version needs tens of GB of
  Python object overhead and cannot run (PLANNING.md FASE 11).
- :class:`LegacyCostTable` — the original dict-of-tuples breadth-first
  implementation, kept verbatim as the executable reference for the
  exact-equality tests (``tests/unit/test_cost_table_vectorized.py``). Both
  produce bit-identical tables and candidate pools.
"""

import numpy as np
from numpy.typing import NDArray

from src.constants.strategies import COST_TABLE_CHUNK_ROWS


class CostTable:
    """Hamming-weighted transition-cost table over the hypercube of states.

    Vectorized implementation: the per-node cost vectors for **every** state
    of the m-dimensional hypercube are stored in a single ``(2^m, num_nodes)``
    ``float32`` array (:attr:`table`), where a state's row index is its
    little-endian integer ``Σ state[j]·2^j``. The table is filled level by
    level over the Hamming distance to ``state_start`` with the recurrence

        T(s) = γ(s) · ( D(s) + Σ_{nb ∈ N⁻(s)} T(nb) ),   γ(s) = 1 / 2^{d_H(s)}

    where ``D(s)[i] = |X_i[start] - X_i[s]|`` and ``N⁻(s)`` are the ``d_H(s)``
    neighbors of ``s`` one bit closer to ``state_start`` — exactly the
    accumulation performed by :class:`LegacyCostTable`, so the resulting
    values are bit-identical (same float32 operations in the same order per
    entry; equality covered by ``tests/unit/test_cost_table_vectorized.py``).

    Args:
        flat_data: One raveled probability array per effect n-cube. The array
            for node ``i`` is indexed by the little-endian integer of a
            mechanism substate, so ``flat_data[i][state_int]`` is the marginal
            probability contribution of node ``i`` at that state.
        state_start: Initial mechanism substate as a 0/1 array.
        state_end: Target substate (``1 - state_start``), the hypercube vertex
            antipodal to ``state_start``.

    Attributes:
        table: The ``(2^m, num_nodes)`` float32 cost table, row-indexed by the
            little-endian state integer. Row ``state_start`` is all zeros.
        num_nodes: Number of effect n-cubes (length of every cost vector).
    """

    def __init__(
        self,
        flat_data: list[NDArray[np.float32]],
        state_start: NDArray[np.int8],
        state_end: NDArray[np.int8],
    ) -> None:
        """Keep per-node raveled views (no stacking copy) and build the table.

        Avoiding the ``(num_nodes, 2^m)`` stacked copy of the legacy version
        saves ~3.4 GB at m=n=25; each level gathers directly from the
        individual per-node arrays instead.
        """
        self.state_start = state_start
        self.state_end = state_end
        self.num_nodes = len(flat_data)
        self._flats = [np.ascontiguousarray(flat) for flat in flat_data]
        self._num_dims = int(state_start.size)
        self._powers = 1 << np.arange(self._num_dims, dtype=np.int64)
        self._origin = int(np.dot(state_start.astype(np.int64), self._powers))
        self.table: NDArray[np.float32] = self._build()

    def _build(self) -> NDArray[np.float32]:
        """Fill the table level by level over the Hamming distance to the start.

        States are processed in ascending Hamming-level order so every one-bit
        neighbor toward the origin is already final when a level is computed.
        Levels are processed in row chunks to bound temporary memory.
        """
        num_dims = self._num_dims
        size = 1 << num_dims
        states = np.arange(size, dtype=np.int64)
        dist = _popcount(states ^ self._origin, num_dims)
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
                        flat[chunk].astype(np.float32, copy=False)
                        - origin_values[node]
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
        """Return the per-node cost vector for the ``start -> end`` transition.

        As in the legacy table, transitions are only stored from the initial
        state, so ``state_start`` must equal the table's origin.
        """
        if tuple(state_start) != tuple(self.state_start.tolist()):
            raise KeyError(
                "CostTable solo almacena transiciones desde el estado inicial "
                f"{self.state_start.tolist()}, no desde {list(state_start)}."
            )
        end_int = int(np.dot(np.asarray(state_end, dtype=np.int64), self._powers))
        return self.table[end_int]

    def candidate_bipartitions(self) -> list[list[list[int]]]:
        """Propose bipartition candidates from the cost table.

        Returns a list of ``[present_positions, future_positions]`` selections,
        where ``present_positions`` index into the mechanism dimensions and
        ``future_positions`` index into the effect n-cubes. The pool combines:

        - the ``n`` single-node cuts (each effect node isolated), and
        - for every Hamming level up to the midpoint, the lowest-cost
          assignment of each node to the start side or its complement.

        The per-level scan replicates the legacy semantics exactly: states are
        ranked in the legacy breadth-first order (lexicographic order of the
        flipped-position tuples, realized as descending bit-reversed masks),
        per-state costs accumulate ``min(T[s][i], T[s̄][i])`` over nodes in
        float64 (sequential, same order as the legacy Python loop), and the
        strict ``<`` update keeps the first minimum of the level.
        """
        num_dims = self._num_dims
        n_vars = self.num_nodes
        full_mask = (1 << num_dims) - 1

        candidates: list[list[list[int]]] = [
            [
                [i for i in range(len(self.state_end))],
                [i for i in range(n_vars) if i != idx],
            ]
            for idx in range(n_vars)
        ]

        num_levels = num_dims + 1
        half = (num_levels // 2) + (1 if num_levels % 2 else 0)
        states = np.arange(1 << num_dims, dtype=np.int64)
        dist = _popcount(states ^ self._origin, num_dims)

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
    """Per-element population count of ``num_bits``-bit non-negative integers."""
    remaining = values.astype(np.uint64, copy=True)
    counts = np.zeros(values.shape, dtype=np.uint8)
    for _ in range(num_bits):
        counts += (remaining & np.uint64(1)).astype(np.uint8)
        remaining >>= np.uint64(1)
    return counts


def _bit_reverse(values: NDArray[np.int64], num_bits: int) -> NDArray[np.int64]:
    """Reverse the lowest ``num_bits`` bits of each element.

    Sorting flipped-bit masks by **descending** bit-reversed value enumerates
    the states of a Hamming level in lexicographic order of their
    flipped-position tuples — the exact breadth-first insertion order of the
    legacy table (property verified empirically for m ≤ 10 over every level
    and asserted by the candidate-equality tests).
    """
    reversed_values = np.zeros(values.shape, dtype=np.int64)
    for bit_pos in range(num_bits):
        reversed_values |= ((values >> bit_pos) & 1) << (num_bits - 1 - bit_pos)
    return reversed_values


class LegacyCostTable:
    """Original dict-of-tuples cost table (reference implementation).

    Builds the table with a breadth-first walk that flips, level by level, the
    bits separating ``state_start`` from its antipode, storing one per-node
    cost vector per reached vertex in :attr:`transition_table`. Kept verbatim
    as the executable specification for the equality tests of
    :class:`CostTable`; do **not** use it for n ≳ 20 (the Python dict/tuple
    overhead is ~1 KB per entry × 2^m entries → OOM far below n=25).

    Args:
        flat_data: One raveled probability array per effect n-cube.
        state_start: Initial mechanism substate as a 0/1 array.
        state_end: Target substate (``1 - state_start``).

    Attributes:
        transition_table: Maps ``(start_tuple, end_tuple)`` to the per-node
            cost vector of length ``num_nodes``.
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
        """Expand every vertex at ``level - 1`` toward ``state_end`` by one bit."""
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
        """Store the per-node transition cost vector for ``start -> end``.

        Single-bit jumps read the node-wise absolute difference directly; for
        multi-bit jumps the single-bit neighbor costs are accumulated, and the
        whole vector is finally scaled by ``γ = 1 / 2^{d_H}``.
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
                    cost = cost + self.transition_table[(tuple(state_start), tuple(neighbor))]

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
                [i for i in range(len(self.state_end))],
                [i for i in range(n_vars) if i != idx],
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
