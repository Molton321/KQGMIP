"""Ground-distance metric options for the causal EMD."""

from enum import Enum


class MetricDistance(Enum):
    """Ground distance metrics for the causal EMD computation."""

    HAMMING = "distancia-hamming"
