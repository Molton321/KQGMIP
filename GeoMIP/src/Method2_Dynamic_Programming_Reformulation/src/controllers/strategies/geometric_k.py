"""
geometric_k.py
GeometricSIA extendida para K-particiones (K >= 2).
"""
from __future__ import annotations
import time
import numpy as np

from src.controllers.strategies.geometric import GeometricSIA
from src.funcs.k_partitions import particiones_k_sistema, stirling2
from src.funcs.base import emd_efecto
from src.models.core.system_k import distribucion_marginal_k


class GeometricSIA_K(GeometricSIA):
    """
    Extensión de GeometricSIA que soporta K-particiones.
    K=2 delega al método original (sin overhead).
    K>2 usa find_mip_k().
    """

    def aplicar_estrategia_k(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
        k: int = 3
    ) -> dict:
        """
        Punto de entrada para K-particiones.

        Args:
            condicion: string de bits (ej: "111") — 0 en posición i condicionará esa variable
            alcance: string de bits — 0 en posición i la excluye del alcance
            mecanismo: string de bits — 0 en posición i la excluye del mecanismo
            tpm: matriz de transición de probabilidad
            k: número de particiones (>= 2)

        Returns:
            dict con: phi, particion, tiempo, k, evaluaciones
        """
        if k < 2:
            raise ValueError(f"K debe ser >= 2, recibido k={k}")

        if k == 2:
            resultado = self.aplicar_estrategia(condicion, alcance, mecanismo, tpm)
            return {
                "phi": resultado.perdida,
                "particion": resultado.particion,
                "tiempo": resultado.tiempo_ejecucion,
                "k": 2,
                "evaluaciones": -1,
            }

        # Setup: igual que aplicar_estrategia hasta find_mip()
        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)

        t0 = time.perf_counter()
        resultado = self.find_mip_k(k)
        elapsed = time.perf_counter() - t0

        return {
            "phi": resultado["phi"],
            "particion": resultado["particion"],
            "tiempo": elapsed,
            "k": k,
            "evaluaciones": resultado["evaluaciones"],
        }

    def find_mip_k(self, k: int) -> dict:
        """
        Busca la K-partición de mínimo φ con terminación temprana.
        """
        mejor_phi = float("inf")
        mejor_particion = None
        evaluaciones = 0

        subsistema = self.sia_subsistema
        dist_conjunta = self.sia_dists_marginales

        alcance = subsistema.indices_ncubos
        mecanismo = subsistema.dims_ncubos

        for grupos in particiones_k_sistema(alcance, mecanismo, k):
            evaluaciones += 1

            dist_mip = distribucion_marginal_k(subsistema, grupos)
            phi = emd_efecto(dist_conjunta, dist_mip)

            if phi == 0.0:
                return {"phi": 0.0, "particion": grupos, "evaluaciones": evaluaciones}

            if phi < mejor_phi:
                mejor_phi = phi
                mejor_particion = grupos

        return {
            "phi": mejor_phi,
            "particion": mejor_particion,
            "evaluaciones": evaluaciones,
        }
