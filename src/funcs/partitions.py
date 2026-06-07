from collections.abc import Generator
from itertools import chain, combinations, islice, product

import numpy as np


def generate_candidates(num_vars: int):
    """Generate every variable combination for conditioning (empty up to n-1)."""
    return (combo for r in range(num_vars) for combo in combinations(range(num_vars), r))


def generate_subsystems(variables: np.ndarray | tuple[int, ...]):
    """Generate the cartesian product of every possible purview × mechanism."""
    times = [combo for r in range(len(variables) + 1) for combo in combinations(variables, r)]
    return product(times, times)


def generate_partitions(m: int, n: int) -> Generator[tuple[np.ndarray, np.ndarray]]:
    """
    Generate the binary bipartitions for a subsystem of m effects × n causes.

    Total of non-trivial partitions: 2^(m-1) * 2^n - 1.
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

    # Skip the trivial (all-zero effect / all-zero cause) row to match the legacy enumeration.
    m_row = m_bits[0]
    for j in range(1, n_combinations):
        yield m_row, n_bits[j]
    for i in range(1, m_combinations):
        m_row = m_bits[i]
        for j in range(n_combinations):
            yield m_row, n_bits[j]


def bipartitions(purviews: np.ndarray, mechanisms: np.ndarray, total=None):
    """Generate every non-trivial bipartition of the subsystem."""
    if total is None:
        total = (1 << purviews.size) * (1 << mechanisms.size)
    return islice(
        product(subsets(purviews), subsets(mechanisms)), 1, total - 1
    )


def subsets(arr: np.ndarray):
    """Generate every subset of an array (including the empty one)."""
    return chain.from_iterable(combinations(arr, r) for r in range(len(arr) + 1))
