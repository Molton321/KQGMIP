from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from src.constants.base import INT_ZERO, STR_ONE
from src.models.base.application import application
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
    """
    try:
        from pyemd import emd

        n = u.size
        costs: NDArray[np.float64] = np.empty((n, n))
        distance = select_distance()

        # Build the symmetric ground-cost matrix from the configured distance.
        for i in range(n):
            costs[i, :i] = [distance(i, j) for j in range(i)]
            costs[:i, i] = costs[i, :i]
        np.fill_diagonal(costs, INT_ZERO)

        return emd(u.astype(np.float64), v.astype(np.float64), costs)
    except ImportError as err:
        raise ImportError(
            "pyemd no está instalado. Instálalo con: pip install pyemd"
        ) from err


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
            f"Tiempo EMD no soportado: '{time}'. "
            f"Opciones: {', '.join(sorted(emd_metrics))}"
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
            f"Distancia no soportada: '{distance}'. "
            f"Opciones: {', '.join(sorted(distances))}"
        )
    return distances[distance]


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count(STR_ONE)
