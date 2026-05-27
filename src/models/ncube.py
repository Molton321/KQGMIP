from dataclasses import dataclass, field
from numpy.typing import NDArray
import numpy as np


@dataclass(frozen=True)
class NCube:
    """
    N-cubo n-dimensional indexado para operación rápida en memoria.

    - `indice`: índice original del n-cubo asociado con un literal (0:A, 1:B, 2:C, ...).
    - `dims`: dimensiones activas actuales del n-cubo.
    - `data`: arreglo numpy con los datos indexados según la notación de origen.
    """

    indice: int
    dims: NDArray[np.int8]
    data: np.ndarray
    memo: dict[tuple[tuple[int, int], ...], np.ndarray] = field(default_factory=dict)

    def __post_init__(self):
        if self.dims.size and self.data.shape != (2,) * self.dims.size:
            raise ValueError(
                f"Forma inválida {self.data.shape} para dimensiones {self.dims}"
            )

    def condicionar(
        self,
        indices_condicionados: NDArray[np.int8],
        estado_inicial: NDArray[np.int8],
    ) -> "NCube":
        """
        Aplica condiciones de fondo seleccionando caras del n-cubo
        según las dimensiones y el estado inicial dado.
        """
        numero_dims = self.dims.size
        seleccion = [slice(None)] * numero_dims

        for condicion in indices_condicionados:
            level_arr = numero_dims - (condicion + 1)
            seleccion[level_arr] = estado_inicial[condicion]

        nuevas_dims = np.array(
            [dim for dim in self.dims if dim not in indices_condicionados],
            dtype=np.int8,
        )
        return NCube(
            data=self.data[tuple(seleccion)],
            indice=self.indice,
            dims=nuevas_dims,
        )

    def marginalizar(self, ejes: NDArray[np.int8]) -> "NCube":
        """
        Colapsa una o más dimensiones manteniendo la probabilidad condicional
        (promedio de las caras sobre los ejes dados).
        """
        if tuple(ejes) not in self.memo:
            marginable_axis = np.intersect1d(ejes, self.dims)
            if not marginable_axis.size:
                return self
            numero_dims = self.dims.size - 1
            ejes_locales = tuple(
                numero_dims - dim_idx
                for dim_idx, axis in enumerate(self.dims)
                if axis in marginable_axis
            )
            new_dims = np.array(
                [d for d in self.dims if d not in marginable_axis],
                dtype=np.int8,
            )
            self.memo[tuple(ejes)] = (
                np.mean(self.data, axis=ejes_locales, keepdims=False),
                new_dims,
            )
        return NCube(
            data=self.memo[tuple(ejes)][0],
            dims=self.memo[tuple(ejes)][1],
            indice=self.indice,
        )

    def __str__(self) -> str:
        datos_str = str(self.data).replace("\n", "\n" + " " * 8)
        return (
            f"NCube(index={self.indice}):\n"
            f"    dims={self.dims}\n"
            f"    shape={self.data.shape}\n"
            f"    data=\n        {datos_str}"
        )
