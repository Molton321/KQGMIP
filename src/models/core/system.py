"""IIT system: a collection of :class:`NCube` tensors, one per node.

:class:`System` performs the central transformations of the pipeline —
``condition`` (background conditions), ``subtract`` (build a subsystem),
``bipartition``/``k_partition`` (memoized partitioning) and
``marginal_distribution`` (the distribution fed to the EMD).

The n-cube tensors are stored as ``float32`` (:data:`NCUBE_DTYPE`): this halves
the memory traffic of the ``marginalize`` reduction and the resident footprint
toward the n≈25 ceiling. The dtype is a module constant so
``tests/unit/test_float32_precision.py`` can rebuild the float64 reference.
"""

import numpy as np
from numpy.typing import NDArray

from src.constants.base import BASE_TWO, COLS_IDX, INT_ZERO
from src.constants.errors import ERROR_INCOMPATIBLE_SPACES
from src.funcs.labels import reindex
from src.models.base.application import application
from src.models.core.ncube import NCube
from src.models.core.partition import KPartition
from src.models.enums.notation import Notation

NCUBE_DTYPE = np.float32


class System:
    """
    Manages an IIT system as a collection of n-cubes, one per node.

    Performs the central transformations:
    - `condition`: applies background conditions.
    - `subtract`: removes purviews and mechanisms to obtain a subsystem.
    - `bipartition`: builds a bipartition of the subsystem.
    - `marginal_distribution`: extracts the distribution for the EMD computation.
    """

    def __init__(self, tpm: np.ndarray, initial_state: np.ndarray):
        """Build one float32 n-cube per node from the TPM and initial state.

        For deterministic 0/1 TPMs the marginal means are dyadic and therefore
        exact in float32 at the tested sizes (see :data:`NCUBE_DTYPE`); each
        column is reshaped into a ``(2,)*n`` tensor, reindexed when the notation
        is not little-endian.
        """
        num_nodes = self._validate(tpm, initial_state)
        self.initial_state = initial_state
        self.memo: dict = {}

        tpm = np.asarray(tpm, dtype=NCUBE_DTYPE)
        is_little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
        self.ncubes = tuple(
            NCube(
                index=idx,
                dims=np.array(range(num_nodes), dtype=np.int8),
                data=(
                    tpm[:, idx].reshape((BASE_TWO,) * num_nodes)
                    if is_little_endian
                    else tpm[idx, :][reindex(num_nodes)].reshape((BASE_TWO,) * num_nodes)
                ),
            )
            for idx in range(num_nodes)
        )

    def _validate(self, tpm: np.ndarray, initial_state: np.ndarray) -> int:
        """Check the state length matches the node count; return the node count."""
        num_nodes = tpm.shape[COLS_IDX]
        if initial_state.size != num_nodes:
            raise ValueError(ERROR_INCOMPATIBLE_SPACES(num_nodes))
        return num_nodes

    @property
    def ncube_indices(self) -> np.ndarray:
        """The original node index of each n-cube currently in the system."""
        return np.array([cube.index for cube in self.ncubes], dtype=np.int8)

    @property
    def ncube_dims(self) -> np.ndarray:
        """The active dimensions shared by the system's n-cubes."""
        return self.ncubes[INT_ZERO].dims if len(self.ncubes) > INT_ZERO else np.array([])

    def condition(self, indices: NDArray[np.int8]) -> System:
        """Apply background conditions: drop the given dimensions by selecting
        the initial state on each of them."""
        valid_indices = np.intersect1d(self.ncube_indices, indices)
        if not valid_indices.size:
            return self
        new_system = System.__new__(System)
        new_system.initial_state = self.initial_state
        new_system.memo = {}
        new_system.ncubes = tuple(
            cube.condition(valid_indices, self.initial_state)
            for cube in self.ncubes
            if cube.index not in valid_indices
        )
        return new_system

    def subtract(
        self,
        purview_idx: NDArray[np.int8],
        mechanism_dims: NDArray[np.int8],
    ) -> System:
        """Build a subsystem by removing the purview n-cubes and marginalizing
        the mechanism dimensions."""
        valid_effects = np.setdiff1d(self.ncube_indices, purview_idx)
        new_system = System.__new__(System)
        new_system.initial_state = self.initial_state
        new_system.memo = {}
        new_system.ncubes = tuple(
            cube.marginalize(mechanism_dims) for cube in self.ncubes if cube.index in valid_effects
        )
        return new_system

    def bipartition(
        self,
        purview: NDArray[np.int8],
        mechanism: NDArray[np.int8],
    ) -> System:
        """Build a (memoized) bipartition of the subsystem.

        Membership is tested with plain Python sets over the tiny index arrays,
        avoiding the heavy fixed cost of ``np.setdiff1d`` / numpy ``in`` in this
        hot loop.
        """
        new_system = System.__new__(System)
        new_system.initial_state = self.initial_state
        new_system.memo = self.memo

        key = tuple(purview), tuple(mechanism)
        cached = self.memo.get(key)
        if cached is None:
            purview_set = {int(p) for p in purview}
            mechanism_set = {int(m) for m in mechanism}
            cached = tuple(
                (
                    cube.marginalize(
                        np.array(
                            [d for d in cube.dims if int(d) not in mechanism_set],
                            dtype=np.int8,
                        )
                    )
                    if int(cube.index) in purview_set
                    else cube.marginalize(mechanism)
                )
                for cube in self.ncubes
            )
            self.memo[key] = cached

        new_system.ncubes = cached
        return new_system

    def bipartition_marginal_distribution(
        self,
        purview: NDArray[np.int8],
        mechanism: NDArray[np.int8],
    ) -> NDArray[np.float32]:
        """Marginal distribution of a bipartition, computed locally per cube.

        Returns exactly ``bipartition(purview, mechanism).marginal_distribution()``
        but without materializing any marginalized tensor: each cube's value is
        obtained with :meth:`NCube.marginal_value` in O(2^{dropped dims})
        instead of the O(2^{all dims}) full reduction — the QNodes hot path
        toward n=25 (PLANNING.md FASE 11). Results are memoized per cut.
        """
        key = ("local", tuple(purview), tuple(mechanism))
        cached = self.memo.get(key)
        if cached is None:
            little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
            purview_set = {int(p) for p in purview}
            mechanism_set = {int(m) for m in mechanism}
            state = self.initial_state
            distribution = np.empty(len(self.ncubes), dtype=NCUBE_DTYPE)
            for i, cube in enumerate(self.ncubes):
                if int(cube.index) in purview_set:
                    axes = np.array(
                        [d for d in cube.dims if int(d) not in mechanism_set],
                        dtype=np.int8,
                    )
                else:
                    axes = mechanism
                distribution[i] = cube.marginal_value(axes, state, little_endian)
            cached = distribution
            self.memo[key] = cached
        return cached

    def k_partition_marginal_distribution(self, partition: KPartition) -> NDArray[np.float32]:
        """Marginal distribution of a k-partition, computed locally per cube.

        Returns exactly ``k_partition(partition).marginal_distribution()`` via
        :meth:`NCube.marginal_value` (same dropped axes as ``k_partition``),
        skipping the per-candidate full-tensor reductions of the δ_k fitness —
        the refinement hot path shared by KGeoMIP and KQNodes (FASE 11).
        """
        future_to_mechanism = self._validated_block_mapping(partition)

        little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
        state = self.initial_state
        distribution = np.empty(len(self.ncubes), dtype=NCUBE_DTYPE)
        for i, cube in enumerate(self.ncubes):
            axes = np.setdiff1d(cube.dims, future_to_mechanism[cube.index])
            distribution[i] = cube.marginal_value(axes, state, little_endian)
        return distribution

    def _validated_block_mapping(self, partition: KPartition) -> dict[int, NDArray[np.int8]]:
        """Check the partition universes and map each future index to its
        paired mechanism block (shared by ``k_partition`` and its local
        marginal variant)."""
        current_future_universe = tuple(sorted(int(i) for i in self.ncube_indices.tolist()))
        current_present_universe = tuple(sorted(int(i) for i in self.ncube_dims.tolist()))

        if partition.future_universe != current_future_universe:
            raise ValueError(
                "KPartition future universe does not match subsystem future indices. "
                f"Expected {current_future_universe}, got {partition.future_universe}."
            )
        if partition.present_universe != current_present_universe:
            raise ValueError(
                "KPartition present universe does not match subsystem mechanism indices. "
                f"Expected {current_present_universe}, got {partition.present_universe}."
            )

        future_to_mechanism: dict[int, NDArray[np.int8]] = {}
        for purview_block, mechanism_block in partition.signature:
            mechanism_arr = np.array(mechanism_block, dtype=np.int8)
            for future_idx in purview_block:
                future_to_mechanism[future_idx] = mechanism_arr
        return future_to_mechanism

    def k_partition(self, partition: KPartition) -> System:
        """Build a k-partitioned subsystem from a validated ``KPartition``.

        For each future n-cube, this method keeps the mechanism dimensions paired
        with that future block and marginalizes the remaining dimensions.
        """
        future_to_mechanism = self._validated_block_mapping(partition)

        new_system = System.__new__(System)
        new_system.initial_state = self.initial_state
        new_system.memo = {}
        new_system.ncubes = tuple(
            cube.marginalize(np.setdiff1d(cube.dims, future_to_mechanism[cube.index]))
            for cube in self.ncubes
        )
        return new_system

    def marginal_distribution(self) -> NDArray[np.float32]:
        """Extract the marginal distribution evaluated at the initial state.

        Hot path: the notation is resolved once (instead of per node inside
        ``select_state``), and the per-node substate index is built inline. The
        access order matches ``select_state`` exactly, so the result is
        unchanged.
        """
        distribution = np.empty(len(self.ncubes), dtype=np.float32)
        little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
        state = self.initial_state
        for i, cube in enumerate(self.ncubes):
            if cube.dims.size:
                substate = tuple(int(state[j]) for j in cube.dims)
                distribution[i] = cube.data[substate[::-1] if little_endian else substate]
            else:
                distribution[i] = cube.data
        return distribution

    def __str__(self) -> str:
        cubes_info = "\n".join(str(c) for c in self.ncubes)
        return (
            f"\nSystem(indices={self.ncube_indices}, dims={self.ncube_dims})"
            f"\nInitial state: {self.initial_state}"
            f"\nNCubes:\n{cubes_info}"
        )
