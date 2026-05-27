import numpy as np
from numpy.typing import NDArray

from src.constants.base import BASE_TWO, COLS_IDX, INT_ZERO
from src.constants.errors import ERROR_ESPACIOS_INCOMPATIBLES
from src.funcs.labels import reindexar, seleccionar_estado
from src.base.application import aplicacion
from src.models.ncube import NCube
from src.models.enums.notation import Notation


class System:
    """
    Gestiona un sistema IIT como colección de n-cubos, uno por nodo.

    Opera las transformaciones centrales:
    - `condicionar`: aplica condiciones de fondo (background conditions).
    - `substraer`: elimina alcances y mecanismos para obtener un subsistema.
    - `bipartir`: genera una bipartición del subsistema.
    - `distribucion_marginal`: extrae la distribución para cálculo de EMD.
    """

    def __init__(self, tpm: np.ndarray, estado_inicio: np.ndarray):
        num_nodos = self._validar(tpm, estado_inicio)
        self.estado_inicial = estado_inicio
        self.memo = {}

        es_little_endian = aplicacion.notacion_indexado == Notation.LIL_ENDIAN.value
        self.ncubos = tuple(
            NCube(
                indice=idx,
                dims=np.array(range(num_nodos), dtype=np.int8),
                data=(
                    tpm[:, idx].reshape((BASE_TWO,) * num_nodos)
                    if es_little_endian
                    else tpm[idx, :][reindexar(num_nodos)].reshape((BASE_TWO,) * num_nodos)
                ),
            )
            for idx in range(num_nodos)
        )

    def _validar(self, tpm: np.ndarray, estado_inicio: np.ndarray) -> int:
        num_nodos = tpm.shape[COLS_IDX]
        if estado_inicio.size != num_nodos:
            raise ValueError(ERROR_ESPACIOS_INCOMPATIBLES(num_nodos))
        return num_nodos

    @property
    def indices_ncubos(self) -> np.ndarray:
        return np.array([cube.indice for cube in self.ncubos], dtype=np.int8)

    @property
    def dims_ncubos(self) -> np.ndarray:
        return (
            self.ncubos[INT_ZERO].dims if len(self.ncubos) > INT_ZERO else np.array([])
        )

    def condicionar(self, indices: NDArray[np.int8]) -> "System":
        """Aplica condiciones de fondo: elimina dimensiones indicadas seleccionando
        el estado inicial en cada una."""
        indices_validos = np.intersect1d(self.indices_ncubos, indices)
        if not indices_validos.size:
            return self
        nuevo = System.__new__(System)
        nuevo.estado_inicial = self.estado_inicial
        nuevo.memo = {}
        nuevo.ncubos = tuple(
            cube.condicionar(indices_validos, self.estado_inicial)
            for cube in self.ncubos
            if cube.indice not in indices_validos
        )
        return nuevo

    def substraer(
        self,
        alcance_idx: NDArray[np.int8],
        mecanismo_dims: NDArray[np.int8],
    ) -> "System":
        """Genera un subsistema eliminando n-cubos del alcance y marginalizando
        dimensiones del mecanismo."""
        futuros_validos = np.setdiff1d(self.indices_ncubos, alcance_idx)
        nuevo = System.__new__(System)
        nuevo.estado_inicial = self.estado_inicial
        nuevo.memo = {}
        nuevo.ncubos = tuple(
            cube.marginalizar(mecanismo_dims)
            for cube in self.ncubos
            if cube.indice in futuros_validos
        )
        return nuevo

    def bipartir(
        self,
        alcance: NDArray[np.int8],
        mecanismo: NDArray[np.int8],
    ) -> "System":
        """Genera una bipartición del subsistema. Memoiza los resultados."""
        nuevo = System.__new__(System)
        nuevo.estado_inicial = self.estado_inicial
        nuevo.memo = self.memo

        clave = tuple(alcance), tuple(mecanismo)
        if clave not in self.memo:
            self.memo[clave] = tuple(
                cubo.marginalizar(np.setdiff1d(cubo.dims, mecanismo))
                if cubo.indice in alcance
                else cubo.marginalizar(mecanismo)
                for cubo in self.ncubos
            )

        nuevo.ncubos = self.memo[clave]
        return nuevo

    def distribucion_marginal(self) -> NDArray[np.float32]:
        """Extrae la distribución marginal evaluada en el estado inicial."""
        distribucion = np.empty(self.indices_ncubos.size, dtype=np.float32)
        for i, ncubo in enumerate(self.ncubos):
            probabilidad = ncubo.data
            if ncubo.dims.size:
                inicial = tuple(self.estado_inicial[j] for j in ncubo.dims)
                probabilidad = ncubo.data[seleccionar_estado(inicial)]
            distribucion[i] = probabilidad
        return distribucion

    def __str__(self) -> str:
        cubos_info = "\n".join(str(c) for c in self.ncubos)
        return (
            f"\nSystem(indices={self.indices_ncubos}, dims={self.dims_ncubos})"
            f"\nInitial state: {self.estado_inicial}"
            f"\nNCubes:\n{cubos_info}"
        )
