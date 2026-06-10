"""Enumeration of subsets and non-trivial bipartitions of an index set,
used for computing the power set of a system and the MIP of a partition."""

from itertools import chain, combinations, islice, product

import numpy as np


def bipartitions(purviews: np.ndarray, mechanisms: np.ndarray, total=None):
    """Generate every non-trivial bipartition of the given purviews and mechanisms.
    If total is given, only generate the first total bipartitions in lexicographic order.
    """
    if total is None:
        total = (1 << purviews.size) * (1 << mechanisms.size)
    return islice(product(subsets(purviews), subsets(mechanisms)), 1, total - 1)


def subsets(arr: np.ndarray):
    """Generate every subset of an array (including the empty one)."""
    return chain.from_iterable(combinations(arr, r) for r in range(len(arr) + 1))
