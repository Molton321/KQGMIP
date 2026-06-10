"""
Global application configuration and state management. This module defines
the Application class, which holds global settings for the application,
such as the random seed, selected sample network page, distance metric,
notation, and profiling options. The Application instance is a singleton
that can be imported and modified by any module to access or change the
application's settings.
"""

from src.models.enums.distance import MetricDistance
from src.models.enums.notation import Notation
from src.models.enums.temporal_emd import TimeEMD


class Application:
    """
    Class for global application configuration and state.
    This is a singleton instance that can be imported and
    modified by any module to access or change the application's settings.
    """

    def __init__(self) -> None:
        self.numpy_seed: int = 73
        self.sample_network_page: str = "A"
        self.metric_distance: str = MetricDistance.HAMMING.value
        self.indexing_notation: str = Notation.LIL_ENDIAN.value
        self.emd_time: str = TimeEMD.EMD_EFFECT.value
        self.profiler_enabled: bool = True

    def set_sample_network_page(self, page: str) -> None:
        """Select the sample-network page (A, B, ...) to auto-load."""
        self.sample_network_page = page

    def set_notation(self, kind: Notation) -> None:
        """Set the binary index notation used to address the n-cubes."""
        self.indexing_notation = kind.value if isinstance(kind, Notation) else str(kind)

    def set_emd_time(self, kind: TimeEMD) -> None:
        """Set the temporal EMD variant (cause / effect / integrated)."""
        self.emd_time = kind.value if isinstance(kind, TimeEMD) else str(kind)

    def enable_profiling(self) -> None:
        """Turn HTML profiling on (profiles written under review/profiling/)."""
        self.profiler_enabled = True

    def disable_profiling(self) -> None:
        """Turn HTML profiling off."""
        self.profiler_enabled = False


application = Application()
