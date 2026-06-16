"""Earth Mover's Distance (EMD) for both the effect and cause distributions
in the context of SIA. The EMD is a measure of the distance between two probability
distributions, and it is used to quantify the loss of information when partitioning a subsystem.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from pyemd import emd

from src.constants.base import INT_ZERO, STR_ONE
from src.models.base.application import application
from src.models.core.partition import KPartition
from src.models.core.system import System
from src.models.enums.distance import MetricDistance
from src.models.enums.temporal_emd import TimeEMD


def effect_emd(u: NDArray[np.float32], v: NDArray[np.float32]) -> float:
    """The ground distance is the L1 distance between the probability values of the
    distributions. This is equivalent to the total variation distance, which is half
    of the L1 distance, but we keep it as the L1 distance for consistency with the
    causal EMD, which also uses the L1 distance as the ground distance.
    """
    return float(np.sum(np.abs(u - v)))


def causal_emd(u: NDArray[np.float64], v: NDArray[np.float64]) -> float:
    """The ground distance is defined by the configured distance function between
    state indices. The EMD is calculated with the pyemd library, which requires
    a cost matrix of shape (n, n) where n is the number of states in the
    distribution.
    """
    n = u.size
    costs: NDArray[np.float64] = np.empty((n, n))
    distance = select_distance()

    for i in range(n):
        costs[i, :i] = [distance(i, j) for j in range(i)]
        costs[:i, i] = costs[i, :i]
    np.fill_diagonal(costs, INT_ZERO)

    return emd(u.astype(np.float64), v.astype(np.float64), costs)


def select_emd() -> Callable[[NDArray[np.float32], NDArray[np.float32]], float]:
    """Return the EMD function configured in the application."""
    emd_metrics: dict[str, Callable[..., float]] = {
        TimeEMD.EMD_EFFECT.value: effect_emd,
        TimeEMD.EMD_CAUSE.value: causal_emd,
    }
    time = application.emd_time
    if isinstance(time, TimeEMD):
        time = time.value

    if time not in emd_metrics:
        raise ValueError(
            f"Tiempo EMD no soportado: '{time}'. Opciones: {', '.join(sorted(emd_metrics))}"
        )
    return emd_metrics[time]


def select_distance() -> Callable[[int, int], int]:
    """Return the configured ground-distance function (for the causal EMD)."""
    distances = {
        MetricDistance.HAMMING.value: hamming_distance,
    }
    distance = application.metric_distance
    if isinstance(distance, MetricDistance):
        distance = distance.value

    if distance not in distances:
        raise ValueError(
            f"Distancia no soportada: '{distance}'. Opciones: {', '.join(sorted(distances))}"
        )
    return distances[distance]


def hamming_distance(a: int, b: int) -> int:
    """Hamming distance between two state indices (popcount of a ^ b)."""
    return bin(a ^ b).count(STR_ONE)


def delta_k(
    subsystem: System,
    partition: KPartition,
    baseline_distribution: NDArray[np.float32] | None = None,
) -> tuple[float, NDArray[np.float32]]:
    """Calculate the δ_k loss of a k-partition by comparing the original marginal
    distribution to the partitioned distribution with the configured EMD function.
    """
    original = baseline_distribution
    if original is None:
        original = subsystem.marginal_distribution()

    partitioned_distribution = subsystem.k_partition_marginal_distribution(partition)
    return effect_emd(original, partitioned_distribution), partitioned_distribution
