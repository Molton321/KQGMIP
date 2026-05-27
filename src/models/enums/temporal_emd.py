from enum import Enum


class TimeEMD(Enum):
    """Variantes temporales de la Earth Mover's Distance."""

    EMD_EFECTO = "emd-effect"
    EMD_CAUSA = "emd-cause"
    EMD_INTEGRADA = "emd-cause-effect"
