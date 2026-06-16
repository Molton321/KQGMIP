"""Single-node n-cube: one TPM column with dimensions for each node,
used for conditioning and marginalization.

Despite being a frozen dataclass, (memo) and (value_memo) dicts are
**mutated in-place** by :meth:`marginalize` and :meth:`marginal_value`
for performance (caching).  Do not rely on immutability of these fields.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class NCube:
    """
    Represents a single column of the TPM as an n-cube, where each dimension corresponds
    to a node in the system. The data is stored as a NumPy array, and the dimensions are
    tracked as an array of node indices. This structure allows for efficient conditioning
    and marginalization operations by selecting faces of the n-cube and averaging over
    specified axes, respectively. Caching is used to avoid redundant computations for the
    same conditioning or marginalization operations.
    """

    index: int
    dims: NDArray[np.int8]
    data: np.ndarray
    memo: dict[tuple[int, ...], tuple[np.ndarray, NDArray[np.int8]]] = field(
        default_factory=dict
    )
    value_memo: dict[tuple, np.floating] = field(default_factory=dict)

    def __post_init__(self):
        if self.dims.size and self.data.shape != (2,) * self.dims.size:
            raise ValueError(
                f"Forma inválida {self.data.shape} para dimensiones {self.dims}"
            )

    def condition(
        self,
        conditioned_indices: NDArray[np.int8],
        initial_state: NDArray[np.int8],
    ) -> NCube:
        """
        Apply background conditions by selecting faces of the n-cube
        according to the dimensions and the given initial state.
        """
        num_dims = self.dims.size
        selection = [slice(None)] * num_dims

        for cond_idx in conditioned_indices:
            level = num_dims - (cond_idx + 1)
            selection[level] = initial_state[cond_idx]

        new_dims = np.array(
            [dim for dim in self.dims if dim not in conditioned_indices],
            dtype=np.int8,
        )
        return NCube(
            data=self.data[tuple(selection)],
            index=self.index,
            dims=new_dims,
        )

    def marginal_value(
        self,
        axes: NDArray[np.int8],
        initial_state: NDArray[np.int8],
        little_endian: bool,
    ) -> np.floating:
        """Compute the marginal value by averaging over specified axes while keeping
        the others fixed according to the initial state.
        Caches results to avoid redundant computations.
        """
        axes_set = {int(a) for a in axes}
        key = (little_endian, *(int(d) for d in self.dims if int(d) in axes_set))
        cached = self.value_memo.get(key)
        if cached is None:
            num_dims = self.dims.size - 1
            selection: list[slice | int] = [slice(None)] * self.dims.size
            for dim_idx, dim in enumerate(self.dims):
                if int(dim) not in axes_set:
                    axis = num_dims - dim_idx if little_endian else dim_idx
                    selection[axis] = int(initial_state[dim])
            cached = np.asarray(self.data[tuple(selection)]).mean()
            self.value_memo[key] = cached
        return cached

    def marginalize(self, axes: NDArray[np.int8]) -> NCube:
        """Marginalize over specified axes by averaging the data
        and removing the corresponding dimensions.
        Caches results to avoid redundant computations for the same axes."""
        key = tuple(int(a) for a in axes)
        cached = self.memo.get(key)
        if cached is None:
            axes_set = set(key)
            num_dims = self.dims.size - 1
            local_axes = tuple(
                num_dims - dim_idx
                for dim_idx, axis in enumerate(self.dims)
                if int(axis) in axes_set
            )
            if not local_axes:
                return self
            remaining_dims = np.array(
                [d for d in self.dims if int(d) not in axes_set],
                dtype=np.int8,
            )
            cached = (
                np.mean(self.data, axis=local_axes, keepdims=False),
                remaining_dims,
            )
            self.memo[key] = cached
        return NCube(data=cached[0], dims=cached[1], index=self.index)

    def __str__(self) -> str:
        data_str = str(self.data).replace("\n", "\n" + " " * 8)
        return (
            f"NCube(index={self.index}):\n"
            f"    dims={self.dims}\n"
            f"    shape={self.data.shape}\n"
            f"    data=\n        {data_str}"
        )
