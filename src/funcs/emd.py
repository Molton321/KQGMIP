from typing import Callable

import numpy as np
from numpy.typing import NDArray

from src.constants.base import INT_ZERO, STR_ONE
from src.base.application import aplicacion
from src.models.enums.distance import MetricDistance
from src.models.enums.temporal_emd import TimeEMD


def emd_efecto(u: NDArray[np.float32], v: NDArray[np.float32]) -> float:
    """
    EMD analítica para el repertorio efecto (presente → futuro).

    Bajo independencia condicional, la EMD entre dos distribuciones marginales
    es la suma de las diferencias absolutas nodo a nodo.
    """
    return float(np.sum(np.abs(u - v)))


def emd_causal(u: NDArray[np.float64], v: NDArray[np.float64]) -> float:
    """
    EMD para el repertorio causal (presente → pasado) usando distancia de Hamming
    como métrica de suelo. Requiere el paquete `pyemd`.
    """
    try:
        from pyemd import emd

        n = u.size
        costos: NDArray[np.float64] = np.empty((n, n))
        distancia = seleccionar_distancia()

        for i in range(n):
            costos[i, :i] = [distancia(i, j) for j in range(i)]
            costos[:i, i] = costos[i, :i]
        np.fill_diagonal(costos, INT_ZERO)

        return emd(u.astype(np.float64), v.astype(np.float64), costos)
    except ImportError:
        raise ImportError(
            "pyemd no está instalado. Instálalo con: pip install pyemd"
        )


def seleccionar_emd() -> Callable[[NDArray[np.float32], NDArray[np.float32]], float]:
    """Devuelve la función EMD configurada en la aplicación."""
    emd_metricas = {
        TimeEMD.EMD_EFECTO.value: emd_efecto,
        TimeEMD.EMD_CAUSA.value: emd_causal,
    }
    tiempo = aplicacion.tiempo_emd
    if isinstance(tiempo, TimeEMD):
        tiempo = tiempo.value

    if tiempo not in emd_metricas:
        raise ValueError(
            f"Tiempo EMD no soportado: '{tiempo}'. "
            f"Opciones: {', '.join(sorted(emd_metricas))}"
        )
    return emd_metricas[tiempo]


def seleccionar_distancia() -> Callable[[int, int], int]:
    """Devuelve la función de distancia de suelo configurada (para EMD causal)."""
    distancias = {
        MetricDistance.HAMMING.value: hamming_distance,
    }
    distancia = aplicacion.distancia_metrica
    if isinstance(distancia, MetricDistance):
        distancia = distancia.value

    if distancia not in distancias:
        raise ValueError(
            f"Distancia no soportada: '{distancia}'. "
            f"Opciones: {', '.join(sorted(distancias))}"
        )
    return distancias[distancia]


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count(STR_ONE)
