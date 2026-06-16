"""Abstract base (Template Method) for every IIT analysis strategy,
responsible for preparing the subsystem through conditioning and subtraction.
"""

import time
from abc import ABC, abstractmethod

import numpy as np
import numpy.typing as npt

from src.constants.base import COLS_IDX, FLOAT_ZERO, STR_ZERO
from src.constants.errors import ERROR_INCOMPATIBLE_SIZES
from src.constants.tags import SIA_PREPARATION_TAG
from src.middlewares.slogger import SafeLogger
from src.models.core.solution import Solution
from src.models.core.system import System


class SIA(ABC):
    """
    Abstract base class for every IIT analysis strategy.
    Receives the TPM and the initial state, builds the subsystem through
    conditioning and subtraction, and leaves it ready for the strategies.
    Subclasses must implement apply_strategy(condition, purview, mechanism).
    """

    def __init__(self, tpm: np.ndarray, initial_state: str) -> None:
        self.tpm = tpm
        self.initial_state = initial_state
        self.sia_logger = SafeLogger(SIA_PREPARATION_TAG)
        self.sia_subsystem: System
        self.sia_marginal_dists: npt.NDArray[np.float32]
        self.sia_start_time: float = FLOAT_ZERO

    @abstractmethod
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Implement the MIP search algorithm."""

    def sia_prepare_subsystem(
        self, condition: str, purview: str, mechanism: str
    ) -> None:
        """
        Prepare the subsystem for the strategy by conditioning on
        (condition) and subtracting (purview) and (mechanism).
        """
        if not self._check_parameters(condition, purview, mechanism):
            raise ValueError(ERROR_INCOMPATIBLE_SIZES)

        conditioned_dims = np.array(
            [i for i, b in enumerate(condition) if b == STR_ZERO], dtype=np.int8
        )
        purview_dims = np.array(
            [i for i, b in enumerate(purview) if b == STR_ZERO], dtype=np.int8
        )
        mechanism_dims = np.array(
            [i for i, b in enumerate(mechanism) if b == STR_ZERO], dtype=np.int8
        )
        state_dims = np.array([int(b) for b in self.initial_state], dtype=np.int8)

        full_system = System(self.tpm, state_dims)
        self.sia_logger.critic("Sistema completo creado.")

        candidate = full_system.condition(conditioned_dims)
        self.sia_logger.critic("Sistema candidato creado.")

        subsystem = candidate.subtract(purview_dims, mechanism_dims)
        self.sia_logger.critic("Subsistema creado.")

        self.sia_subsystem = subsystem
        self.sia_marginal_dists = subsystem.marginal_distribution()
        self.sia_start_time = time.perf_counter()

    def _check_parameters(self, condition: str, purview: str, mechanism: str) -> bool:
        """Return True if every parameter has the correct length."""
        n = self.tpm.shape[COLS_IDX]
        return (
            len(self.initial_state)
            == len(condition)
            == len(purview)
            == len(mechanism)
            == n
        )
