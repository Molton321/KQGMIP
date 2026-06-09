"""Earth Mover's Distance variants and the δ_k partition loss.

Provides the analytic effect-repertoire EMD (a sum of node-wise absolute
differences under conditional independence), the optional ``pyemd``-backed causal
EMD, the selectors that read the configured variant/metric from ``application``,
and :func:`delta_k` — the single loss every k-partition strategy is scored with.
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
    """
    Analytic EMD for the effect repertoire (present → future).

    Under conditional independence, the EMD between two marginal distributions
    is the sum of the node-by-node absolute differences.
    """
    return float(np.sum(np.abs(u - v)))


def causal_emd(u: NDArray[np.float64], v: NDArray[np.float64]) -> float:
    """
    EMD for the causal repertoire (present → past) using the Hamming distance
    as the ground metric. Requires the `pyemd` package.

    The symmetric ground-cost matrix is built once from the configured distance
    before delegating to ``pyemd.emd``.
    """
    try:
        n = u.size
        costs: NDArray[np.float64] = np.empty((n, n))
        distance = select_distance()

        for i in range(n):
            costs[i, :i] = [distance(i, j) for j in range(i)]
            costs[:i, i] = costs[i, :i]
        np.fill_diagonal(costs, INT_ZERO)

        return emd(u.astype(np.float64), v.astype(np.float64), costs)
    except ImportError as err:
        raise ImportError("pyemd no está instalado. Instálalo con: pip install pyemd") from err


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
    """Hamming distance between two state indices (popcount of ``a ^ b``)."""
    return bin(a ^ b).count(STR_ONE)


def delta_k(
    subsystem: System,
    partition: KPartition,
    baseline_distribution: NDArray[np.float32] | None = None,
) -> tuple[float, NDArray[np.float32]]:
    """Compute δ_k for a validated k-partition on a subsystem.

    Definition used in this project:
    δ_k = EMD(P(subsystem), P(partitioned_subsystem))

    where ``partitioned_subsystem`` is built by the tensor-product style
    reconstruction induced by the paired purview/mechanism blocks.

    Returns:
        A tuple ``(loss, partition_distribution)``.
    """
    original = baseline_distribution
    if original is None:
        original = subsystem.marginal_distribution()

    partitioned_distribution = subsystem.k_partition_marginal_distribution(partition)
    return effect_emd(original, partitioned_distribution), partitioned_distribution
