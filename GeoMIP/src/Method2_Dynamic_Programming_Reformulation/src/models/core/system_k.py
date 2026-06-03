"""
system_k.py
Extensión de System para K-particiones. No modifica system.py.
"""
from __future__ import annotations
import numpy as np
from .system import System
from src.funcs.k_partitions import tensor_product_k


class SystemK(System):
    """
    Hereda todo de System. Agrega distribucion_marginal_k() para K grupos.
    """

    def distribucion_marginal_k(
        self,
        grupos: tuple[tuple[np.ndarray, np.ndarray], ...]
    ) -> np.ndarray:
        """
        Calcula el tensor product de K distribuciones marginales.

        Args:
            grupos: K pares (alcance_i, mecanismo_i)

        Returns:
            np.ndarray de tamaño 2^N (producto Kronecker de K distribuciones)
        """
        dists = [
            self.bipartir(alcance_i, mecanismo_i).distribucion_marginal()
            for alcance_i, mecanismo_i in grupos
        ]
        return tensor_product_k(dists)


def distribucion_marginal_k(
    sistema: System,
    grupos: tuple[tuple[np.ndarray, np.ndarray], ...]
) -> np.ndarray:
    """
    Función standalone equivalente a SystemK.distribucion_marginal_k.
    Funciona sobre cualquier instancia de System sin necesidad de subclasificar.
    """
    dists = [
        sistema.bipartir(alcance_i, mecanismo_i).distribucion_marginal()
        for alcance_i, mecanismo_i in grupos
    ]
    return tensor_product_k(dists)
