from enum import Enum


class TimeEMD(Enum):
    """Temporal variants of the Earth Mover's Distance."""

    EMD_EFFECT = "emd-effect"
    EMD_CAUSE = "emd-cause"
    EMD_INTEGRATED = "emd-cause-effect"
