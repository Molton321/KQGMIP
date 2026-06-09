"""Global configuration singleton for the IIT framework.

Exposes the :data:`application` singleton that strategies, models and the EMD
read directly: random seed, sample-network page, ground metric, index notation,
temporal EMD variant and the profiling switch. Set it in ``exec.py`` before a run.
"""

from src.models.enums.distance import MetricDistance
from src.models.enums.notation import Notation
from src.models.enums.temporal_emd import TimeEMD


class Application:
    """
    Global configuration singleton for the IIT framework.

    Configurable attributes:
    - `numpy_seed`: deterministic seed for random network generation.
    - `sample_network_page`: suffix of the network to load (A, B, C...) from data/samples/.
    - `metric_distance`: ground metric for the causal EMD (Hamming by default).
    - `indexing_notation`: binary notation used to index the n-cubes (LIL_ENDIAN by default).
    - `emd_time`: temporal EMD variant to use (effect by default).
    - `profiler_enabled`: stores HTML profiles under review/profiling/ when True.
    """

    def __init__(self) -> None:
        self.numpy_seed: int = 73
        self.sample_network_page: str = "A"
        self.metric_distance: str = MetricDistance.HAMMING.value
        self.indexing_notation: str = Notation.LIL_ENDIAN.value
        self.emd_time: str = TimeEMD.EMD_EFFECT.value
        self.profiler_enabled: bool = True

    def set_sample_network_page(self, page: str) -> None:
        """Select the sample-network page (``A``, ``B``, ...) to auto-load."""
        self.sample_network_page = page

    def set_notation(self, kind: Notation) -> None:
        """Set the binary index notation used to address the n-cubes."""
        self.indexing_notation = kind.value if isinstance(kind, Notation) else str(kind)

    def set_distance(self, kind: MetricDistance) -> None:
        """Set the ground distance metric used by the causal EMD."""
        self.metric_distance = kind.value if isinstance(kind, MetricDistance) else str(kind)

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
