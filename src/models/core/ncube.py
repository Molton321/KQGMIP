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
    memo: dict[tuple[int, ...], tuple[np.ndarray, NDArray[np.int8]]] = field(
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

        Hot path: the index set operations are done with plain Python sets over
        the tiny ``dims`` array (≤ n ints) instead of ``np.intersect1d`` /
        ``np.setdiff1d``, whose fixed overhead dominates for such small inputs.
        The ``np.mean`` reduction over the local axes is unchanged, so the
        result is numerically identical.
        """
        key = tuple(int(a) for a in axes)
        cached = self.memo.get(key)
        if cached is None:
            axes_set = set(key)
            num_dims = self.dims.size - 1
            # Tensor axes (reversed little-endian indexing) of the dims to drop.
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
            cached = (np.mean(self.data, axis=local_axes, keepdims=False), remaining_dims)
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
