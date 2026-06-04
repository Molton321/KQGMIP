"""
system_k.py
Extensión de System para K-particiones. No modifica system.py.

Para K=2 (bipartición): equivalente a bipartir(alcance, mecanismo).distribucion_marginal()
Para K>2: cada ncubo se marginaliza sobre los mecanismos de los otros K-1 grupos,
          igual que bipartir pero extendido a K cortes independientes.
"""
from __future__ import annotations
import numpy as np
from .system import System


class SystemK(System):
    """Hereda todo de System. Agrega distribucion_marginal_k() para K grupos."""

    def distribucion_marginal_k(
        self,
        grupos: tuple[tuple[np.ndarray, np.ndarray], ...]
    ) -> np.ndarray:
        return distribucion_marginal_k(self, grupos)


def distribucion_marginal_k(
    sistema: System,
    grupos: tuple[tuple[np.ndarray, np.ndarray], ...]
) -> np.ndarray:
    """
    Calcula la distribución marginal de un sistema con K-partición.

    Para cada ncubo del sistema, encuentra el grupo al que pertenece (por su índice
    en el alcance del grupo) y lo marginaliza sobre los mecanismos de los otros grupos.
    El resultado tiene la misma dimensión que distribucion_marginal() — un valor por ncubo.

    Args:
        sistema: System (subsistema ya preparado)
        grupos: K pares (alcance_i: np.ndarray, mecanismo_i: np.ndarray)

    Returns:
        np.ndarray de tamaño n (uno por ncubo), comparable con sia_dists_marginales
    """
    # Todos los mecanismos del sistema
    all_mecanismo = (
        np.concatenate([mec for _, mec in grupos])
        if any(len(mec) > 0 for _, mec in grupos)
        else np.array([], dtype=np.int8)
    )

    result = np.empty(len(sistema.ncubos), dtype=np.float32)

    for i, ncubo in enumerate(sistema.ncubos):
        # Encontrar el grupo al que pertenece este ncubo (por indice en alcance)
        group_mec = np.array([], dtype=np.int8)
        for alc_i, mec_i in grupos:
            if len(alc_i) > 0 and ncubo.indice in alc_i:
                group_mec = mec_i
                break

        # Marginalizar sobre mecanismos de otros grupos (= cortar conexiones)
        other_mec = np.setdiff1d(all_mecanismo, group_mec)
        cut = ncubo.marginalizar(other_mec) if other_mec.size > 0 else ncubo

        # Seleccionar probabilidad según estado_inicial
        if cut.dims.size == 0:
            result[i] = 1.0 - float(cut.data)
        else:
            idx = 0
            for bit_pos, dim in enumerate(reversed(cut.dims.tolist())):
                idx |= int(sistema.estado_inicial[dim]) << bit_pos
            result[i] = 1.0 - cut.data.ravel()[idx]

    return result
