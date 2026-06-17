"""IIT system: a collection of :class:NCube tensors, one per node.
Each n-cube represents the conditional distribution of a node given the states of all nodes, and is
indexed by the node it represents. The system supports conditioning, subtraction, and partitioning
operations that modify the n-cubes accordingly, as well as memoization
for efficient repeated computations."""

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
    Each n-cube is a tensor representing the conditional distribution of a node
    given the states of all nodes (the TPM), and is indexed by the node it represents.
    """

    def __init__(self, tpm: np.ndarray, initial_state: np.ndarray):
        """Build one n-cube per node from the TPM and initial state.

        Each NCube stores a *view* into the corresponding column of the shared
        buffer kept on (self._tpm). An integer (0/1) TPM is preserved in its
        compact dtype instead of being cast to float32, so the shared buffer is
        4x smaller; the float32 cast happens lazily where a value is needed.
        """
        num_nodes = self._validate(tpm, initial_state)
        self.initial_state = initial_state
        self.memo: dict = {}
        self._tpm = (
            np.ascontiguousarray(tpm)
            if np.issubdtype(tpm.dtype, np.integer)
            else np.ascontiguousarray(tpm, dtype=NCUBE_DTYPE)
        )
        is_little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
        self.ncubes = tuple(
            NCube(
                index=idx,
                dims=np.array(range(num_nodes), dtype=np.int8),
                data=(
                    self._tpm[:, idx].reshape((BASE_TWO,) * num_nodes)
                    if is_little_endian
                    else np.ascontiguousarray(
                        tpm[idx, :][reindex(num_nodes)], dtype=NCUBE_DTYPE
                    ).reshape((BASE_TWO,) * num_nodes)
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
        return (
            self.ncubes[INT_ZERO].dims if len(self.ncubes) > INT_ZERO else np.array([])
        )

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
            cube.marginalize(mechanism_dims)
            for cube in self.ncubes
            if cube.index in valid_effects
        )
        return new_system

    def bipartition(
        self,
        purview: NDArray[np.int8],
        mechanism: NDArray[np.int8],
    ) -> System:
        """Build a (memoized) bipartition of the subsystem."""
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
        """Marginal distribution of a bipartition, computed locally per cube."""
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

    def k_partition_marginal_distribution(
        self, partition: KPartition
    ) -> NDArray[np.float32]:
        """Marginal distribution of a k-partition, computed locally per cube.
        Each future block is paired with its mechanism block, and the remaining
        dimensions are marginalized out.
        """
        future_to_mechanism = self._validated_block_mapping(partition)

        little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
        state = self.initial_state
        distribution = np.empty(len(self.ncubes), dtype=NCUBE_DTYPE)
        for i, cube in enumerate(self.ncubes):
            mechanism = future_to_mechanism[cube.index]
            axes = np.array(
                [d for d in cube.dims if int(d) not in mechanism], dtype=np.int8
            )
            distribution[i] = cube.marginal_value(axes, state, little_endian)
        return distribution

    def _validated_block_mapping(
        self, partition: KPartition
    ) -> dict[int, frozenset[int]]:
        """Check the partition universes and map each future index to its
        paired mechanism block (shared by k_partition and its local
        marginal variant)."""
        current_future_universe = tuple(
            sorted(int(i) for i in self.ncube_indices.tolist())
        )
        current_present_universe = tuple(
            sorted(int(i) for i in self.ncube_dims.tolist())
        )

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

        future_to_mechanism: dict[int, frozenset[int]] = {}
        for purview_block, mechanism_block in partition.signature:
            mechanism_set = frozenset(int(m) for m in mechanism_block)
            for future_idx in purview_block:
                future_to_mechanism[future_idx] = mechanism_set
        return future_to_mechanism

    def k_partition(self, partition: KPartition) -> System:
        """Build a k-partitioned subsystem from a validated (KPartition).
        For each future n-cube, this method keeps the mechanism dimensions paired
        with that future block and marginalizes the remaining dimensions.
        """
        future_to_mechanism = self._validated_block_mapping(partition)

        new_system = System.__new__(System)
        new_system.initial_state = self.initial_state
        new_system.memo = {}
        new_system.ncubes = tuple(
            cube.marginalize(
                np.array(
                    [
                        d
                        for d in cube.dims
                        if int(d) not in future_to_mechanism[cube.index]
                    ],
                    dtype=np.int8,
                )
            )
            for cube in self.ncubes
        )
        return new_system

    def marginal_distribution(self) -> NDArray[np.float32]:
        """Extract the marginal distribution evaluated at the initial state.
        This is the distribution over the current n-cubes, not the full joint distribution.
        """
        distribution = np.empty(len(self.ncubes), dtype=np.float32)
        little_endian = application.indexing_notation == Notation.LIL_ENDIAN.value
        state = self.initial_state
        for i, cube in enumerate(self.ncubes):
            if cube.dims.size:
                substate = tuple(int(state[j]) for j in cube.dims)
                distribution[i] = cube.data[
                    substate[::-1] if little_endian else substate
                ]
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
