from enum import Enum


class MetricDistance(Enum):
    """Métricas de distancia para el cálculo de EMD causal."""

    HAMMING = "distancia-hamming"
    MANHATTAN = "distancia-manhattan"
    EUCLIDIANA = "distancia-euclidiana"
