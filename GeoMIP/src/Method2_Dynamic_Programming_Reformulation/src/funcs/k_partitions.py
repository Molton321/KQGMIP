"""
k_partitions.py
Generador de K-particiones de conjuntos de nodos para GeoMIP.
"""
from __future__ import annotations
from typing import Generator
import numpy as np
from functools import lru_cache, reduce


def set_partitions_k(
    elements: list,
    k: int
) -> Generator[tuple[tuple, ...], None, None]:
    """
    Genera todas las formas de dividir `elements` en exactamente `k` grupos
    no vacíos, sin repeticiones (orden canónico: primer elemento siempre en grupo 0).
    """
    n = len(elements)
    if k < 1 or k > n:
        return
    if k == 1:
        yield (tuple(elements),)
        return
    if k == n:
        yield tuple((e,) for e in elements)
        return

    def _recurse(idx: int, grupos: list[list]):
        if idx == n:
            if all(g for g in grupos):
                yield tuple(tuple(g) for g in grupos)
            return
        elem = elements[idx]
        no_vacios = sum(1 for g in grupos if g)
        for i in range(len(grupos)):
            if not grupos[i] and i > no_vacios:
                break
            grupos[i].append(elem)
            yield from _recurse(idx + 1, grupos)
            grupos[i].pop()

    yield from _recurse(0, [[] for _ in range(k)])


def particiones_k_sistema(
    alcance: np.ndarray,
    mecanismo: np.ndarray,
    k: int
) -> Generator[tuple, None, None]:
    """
    Genera K-particiones del par (alcance × mecanismo).
    Cada partición es una tupla de K pares (np.ndarray, np.ndarray).
    Descarta particiones donde algún grupo tiene ambos lados vacíos.
    """
    for part_alc in set_partitions_k(alcance.tolist(), k):
        for part_mec in set_partitions_k(mecanismo.tolist(), k):
            grupos = tuple(
                (np.array(part_alc[i], dtype=np.int8), np.array(part_mec[i], dtype=np.int8))
                for i in range(k)
            )
            if all(len(g[0]) > 0 or len(g[1]) > 0 for g in grupos):
                yield grupos


@lru_cache(maxsize=None)
def stirling2(n: int, k: int) -> int:
    """Número de Stirling de segunda especie S(n, k)."""
    if n == 0 and k == 0:
        return 1
    if n == 0 or k == 0:
        return 0
    return k * stirling2(n - 1, k) + stirling2(n - 1, k - 1)


def tensor_product_k(distribuciones: list[np.ndarray]) -> np.ndarray:
    """Tensor product (Kronecker) de K distribuciones."""
    return reduce(np.kron, distribuciones)
