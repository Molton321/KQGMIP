from itertools import chain, combinations, islice, product
from typing import Generator, Tuple, Union

import numpy as np


def generar_candidatos(n_vars: int):
    """Genera todas las combinaciones de variables para condicionamiento (vacío hasta n-1)."""
    return (combo for r in range(n_vars) for combo in combinations(range(n_vars), r))


def generar_subsistemas(vars: tuple[int, ...]):
    """Genera el producto cartesiano de todos los posibles alcances × mecanismos."""
    tiempos = [combo for r in range(len(vars) + 1) for combo in combinations(vars, r)]
    return product(tiempos, tiempos)


def generar_particiones(
    m: int,
    n: int,
    *,
    as_matrix: bool = False,
    as_generator: bool = True,
) -> Union[Generator[Tuple[np.ndarray, np.ndarray], None, None], list]:
    """
    Genera biparticiones binarias para un subsistema de m futuros × n presentes.

    Total de particiones no triviales: 2^(m-1) * 2^n - 1
    """
    if m < 1:
        raise ValueError(f"Alcance trivial: m no puede ser {m}")

    m_combinations = 1 << (m - 1)
    n_combinations = 1 << n

    m_indices = np.arange(m_combinations, dtype=np.uint32)[:, np.newaxis]
    n_indices = np.arange(n_combinations, dtype=np.uint32)[:, np.newaxis]
    m_shifts = np.arange(m - 1, -1, -1, dtype=np.uint8)
    n_shifts = np.arange(n - 1, -1, -1, dtype=np.uint8)

    m_bits = (m_indices >> m_shifts) & 1
    n_bits = (n_indices >> n_shifts) & 1

    if as_generator:
        def partition_generator():
            m_row = m_bits[0]
            for j in range(1, n_combinations):
                yield m_row, n_bits[j]
            for i in range(1, m_combinations):
                m_row = m_bits[i]
                for j in range(n_combinations):
                    yield m_row, n_bits[j]
        return partition_generator()

    if as_matrix:
        total_rows = m_combinations * n_combinations
        result = np.empty((total_rows, m + n), dtype=np.uint8)
        result[:, :m].reshape(m_combinations, n_combinations, m)[:] = m_bits[:, np.newaxis, :]
        result[:, m:].reshape(m_combinations, n_combinations, n)[:] = n_bits
        return result

    return [
        (m_bits[i], n_bits[j])
        for i in range(m_combinations)
        for j in range(n_combinations)
    ]


def biparticiones(alcances: np.ndarray, mecanismos: np.ndarray, total=None):
    """Genera todas las biparticiones no triviales del subsistema."""
    if total is None:
        total = (1 << alcances.size) * (1 << mecanismos.size)
    return islice(
        product(subconjuntos(alcances), subconjuntos(mecanismos)), 1, total - 1
    )


def subconjuntos(arr: np.ndarray):
    """Genera todos los subconjuntos de un arreglo (incluyendo vacío)."""
    return chain.from_iterable(combinations(arr, r) for r in range(len(arr) + 1))
