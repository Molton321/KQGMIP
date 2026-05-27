from abc import ABC, abstractmethod
import time

import numpy as np
import numpy.typing as npt

from src.constants.base import COLS_IDX, FLOAT_ZERO, STR_ZERO
from src.constants.errors import ERROR_INCOMPATIBLE_SIZES
from src.constants.tags import SIA_PREPARATION_TAG
from src.io.logger import SafeLogger
from src.models.system import System


class SIA(ABC):
    """
    Clase base abstracta para todas las estrategias de análisis IIT.

    Recibe la TPM y el estado inicial, construye el subsistema mediante
    condicionamiento y sustracción, y lo deja listo para las estrategias.

    Subclases deben implementar `aplicar_estrategia(condicion, alcance, mecanismo)`.
    """

    def __init__(self, tpm: np.ndarray, estado_inicial: str) -> None:
        self.tpm = tpm
        self.estado_inicial = estado_inicial
        self.sia_logger = SafeLogger(SIA_PREPARATION_TAG)

        self.sia_subsistema: System
        self.sia_dists_marginales: npt.NDArray[np.float32]
        self.sia_tiempo_inicio: float = FLOAT_ZERO

    @abstractmethod
    def aplicar_estrategia(self, condicion: str, alcance: str, mecanismo: str):
        """Implementa el algoritmo de búsqueda de la MIP."""

    def sia_preparar_subsistema(self, condicion: str, alcance: str, mecanismo: str) -> None:
        """
        Construye el subsistema a partir de los parámetros de entrada.

        1. Crea el sistema completo desde la TPM.
        2. Aplica condiciones de fondo (condicionar).
        3. Substrae alcances y mecanismos indicados (substraer).
        4. Guarda el subsistema y su distribución marginal.

        Args:
            condicion: bits en 0 indican las variables a condicionar.
            alcance:   bits en 0 indican las variables futuras a remover.
            mecanismo: bits en 0 indican las variables presentes a remover.
        """
        if not self._chequear_parametros(condicion, alcance, mecanismo):
            raise ValueError(ERROR_INCOMPATIBLE_SIZES)

        dims_condicionadas = np.array(
            [i for i, b in enumerate(condicion) if b == STR_ZERO], dtype=np.int8
        )
        dims_alcance = np.array(
            [i for i, b in enumerate(alcance) if b == STR_ZERO], dtype=np.int8
        )
        dims_mecanismo = np.array(
            [i for i, b in enumerate(mecanismo) if b == STR_ZERO], dtype=np.int8
        )
        dims_estado = np.array([int(b) for b in self.estado_inicial], dtype=np.int8)

        completo = System(self.tpm, dims_estado)
        self.sia_logger.critic("Sistema completo creado.")

        candidato = completo.condicionar(dims_condicionadas)
        self.sia_logger.critic("Sistema candidato creado.")

        subsistema = candidato.substraer(dims_alcance, dims_mecanismo)
        self.sia_logger.critic("Subsistema creado.")

        self.sia_subsistema = subsistema
        self.sia_dists_marginales = subsistema.distribucion_marginal()
        self.sia_tiempo_inicio = time.time()

    def _chequear_parametros(self, condicion: str, alcance: str, mecanismo: str) -> bool:
        """Retorna True si todos los parámetros tienen la longitud correcta."""
        n = self.tpm.shape[COLS_IDX]
        return len(self.estado_inicial) == len(condicion) == len(alcance) == len(mecanismo) == n
