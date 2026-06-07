from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class NCube:
    """
    N-dimensional, indexed n-cube for fast in-memory operation.

    - `index`: original n-cube index tied to a literal (0:A, 1:B, 2:C, ...).
    - `dims`: current active dimensions of the n-cube.
    - `data`: numpy array with the data indexed according to the source notation.
    """

    index: int
    dims: NDArray[np.int8]
    data: np.ndarray
    memo: dict[tuple[tuple[int, int], ...], tuple[np.ndarray, NDArray[np.int8]]] = field(
        default_factory=dict
    )

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

    def marginalize(self, axes: NDArray[np.int8]) -> NCube:
        """
        Collapse one or more dimensions while preserving the conditional
        probability (average of the faces over the given axes).
        """
        if tuple(axes) not in self.memo:
            marginalizable_axes = np.intersect1d(axes, self.dims)
            if not marginalizable_axes.size:
                return self
            num_dims = self.dims.size - 1
            local_axes = tuple(
                num_dims - dim_idx
                for dim_idx, axis in enumerate(self.dims)
                if axis in marginalizable_axes
            )
            remaining_dims = np.array(
                [d for d in self.dims if d not in marginalizable_axes],
                dtype=np.int8,
            )
            self.memo[tuple(axes)] = (
                np.mean(self.data, axis=local_axes, keepdims=False),
                remaining_dims,
            )
        return NCube(
            data=self.memo[tuple(axes)][0],
            dims=self.memo[tuple(axes)][1],
            index=self.index,
        )

    def __str__(self) -> str:
        data_str = str(self.data).replace("\n", "\n" + " " * 8)
        return (
            f"NCube(index={self.index}):\n"
            f"    dims={self.dims}\n"
            f"    shape={self.data.shape}\n"
            f"    data=\n        {data_str}"
        )
