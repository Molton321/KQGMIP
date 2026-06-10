"""Tests for the Phase 7 evaluation metrics."""

import math

from src.funcs.metrics import (
    exact_hit_rate,
    is_exact_hit,
    jaccard_partition_distance,
    relative_phi_error,
    scalability_slope,
    speedup,
)
from src.models.core.partition import KPartition


def _partition(blocks, future, present):
    return KPartition.from_blocks(blocks=blocks, future_universe=future, present_universe=present)


def test_is_exact_hit() -> None:
    assert is_exact_hit(0.25, 0.25)
    assert is_exact_hit(0.2500004, 0.25)  # within tol
    assert not is_exact_hit(0.30, 0.25)


def test_relative_phi_error() -> None:
    assert relative_phi_error(0.5, 0.25) == 1.0  # 100% over
    assert relative_phi_error(0.25, 0.25) == 0.0
    # exact ~0 -> absolute error fallback
    assert relative_phi_error(0.1, 0.0) == 0.1


def test_jaccard_identical_is_zero() -> None:
    blocks = [((0,), (0,)), ((1,), (1,))]
    a = _partition(blocks, (0, 1), (0, 1))
    b = _partition(blocks, (0, 1), (0, 1))
    assert jaccard_partition_distance(a, b) == 0.0


def test_jaccard_different_is_positive() -> None:
    # a: {0,1 together} vs b: {0,1 apart}
    a = _partition([((0, 1), (0, 1)), ((), (2,))], (0, 1), (0, 1, 2))
    b = _partition([((0,), (0,)), ((1,), (1, 2))], (0, 1), (0, 1, 2))
    dist = jaccard_partition_distance(a, b)
    assert 0.0 < dist <= 1.0


def test_speedup() -> None:
    assert speedup(10.0, 2.0) == 5.0
    assert speedup(1.0, 0.0) == float("inf")


def test_exact_hit_rate() -> None:
    # 2 of 3 reach the exact optimum
    assert exact_hit_rate([0.25, 0.5, 0.0], [0.25, 0.25, 0.0]) == 2 / 3


def test_scalability_slope_recovers_exponent() -> None:
    # time = size^2 -> slope ~ 2
    sizes = [2, 4, 8, 16]
    times = [s**2 for s in sizes]
    assert math.isclose(scalability_slope(sizes, times), 2.0, abs_tol=1e-6)
