"""Exact-equality tests: vectorized ``CostTable`` vs ``LegacyCostTable`` (FASE 11).

The vectorized table is the production path toward n=25; the legacy
dict-of-tuples walk is the executable reference. Both must agree **bit by
bit**: same float32 cost vectors for every hypercube vertex and the same
candidate pool (including the lexicographic tie-breaking of the per-level
argmin, which determines the emitted partition on deterministic 0/1 TPMs
where exact cost ties are common).
"""

import numpy as np
import pytest

from src.funcs.cost_table import CostTable
from tests.legacy_cost_table import LegacyCostTable

SIZES = [4, 6, 8, 10]


def _random_instance(num_dims: int, seed: int, deterministic: bool):
    """Build matching (flat_data, state_start, state_end) inputs for both tables."""
    rng = np.random.default_rng(seed)
    if deterministic:
        flat = [
            rng.integers(0, 2, size=2**num_dims).astype(np.float32)
            for _ in range(num_dims)
        ]
    else:
        flat = [rng.random(2**num_dims).astype(np.float32) for _ in range(num_dims)]
    state_start = rng.integers(0, 2, size=num_dims).astype(np.int8)
    state_end = (1 - state_start).astype(np.int8)
    return flat, state_start, state_end


@pytest.mark.parametrize("num_dims", SIZES)
@pytest.mark.parametrize("deterministic", [True, False])
def test_table_is_bit_identical_to_legacy(num_dims: int, deterministic: bool) -> None:
    """Every legacy dict entry must equal the corresponding vectorized row exactly."""
    flat, start, end = _random_instance(
        num_dims, seed=num_dims, deterministic=deterministic
    )
    legacy = LegacyCostTable(flat, start, end)
    vectorized = CostTable(flat, start, end)

    powers = 1 << np.arange(num_dims, dtype=np.int64)
    assert len(legacy.transition_table) == 2**num_dims - 1
    for (_, state), cost in legacy.transition_table.items():
        row = vectorized.table[int(np.dot(np.array(state), powers))]
        assert np.array_equal(row, np.asarray(cost, dtype=np.float32))


@pytest.mark.parametrize("num_dims", SIZES)
@pytest.mark.parametrize("deterministic", [True, False])
@pytest.mark.parametrize("seed_offset", [0, 17, 91])
def test_candidates_identical_to_legacy(
    num_dims: int, deterministic: bool, seed_offset: int
) -> None:
    """The candidate pools must match exactly, including tie-breaking order.

    Deterministic 0/1 TPMs produce dyadic costs with frequent exact ties, so
    this asserts the vectorized per-level argmin reproduces the legacy
    breadth-first first-minimum selection, not just the minimal cost value.
    """
    flat, start, end = _random_instance(
        num_dims, seed=num_dims + seed_offset, deterministic=deterministic
    )
    legacy = LegacyCostTable(flat, start, end)
    vectorized = CostTable(flat, start, end)

    assert vectorized.candidate_bipartitions() == legacy.candidate_bipartitions()


@pytest.mark.parametrize("num_dims", SIZES)
def test_cost_lookup_matches_legacy(num_dims: int) -> None:
    """``cost(start, end)`` must return the same vector as the legacy lookup."""
    flat, start, end = _random_instance(
        num_dims, seed=3 * num_dims + 1, deterministic=False
    )
    legacy = LegacyCostTable(flat, start, end)
    vectorized = CostTable(flat, start, end)

    rng = np.random.default_rng(7)
    for _ in range(20):
        target = rng.integers(0, 2, size=num_dims).astype(np.int8).tolist()
        if target == start.tolist():
            continue
        assert np.array_equal(
            vectorized.cost(start.tolist(), target),
            np.asarray(legacy.cost(start.tolist(), target), dtype=np.float32),
        )


def test_cost_rejects_non_origin_start() -> None:
    """Transitions are only stored from the initial state (legacy contract)."""
    flat, start, end = _random_instance(5, seed=11, deterministic=False)
    vectorized = CostTable(flat, start, end)
    wrong_start = (1 - start).astype(np.int8).tolist()
    with pytest.raises(KeyError):
        vectorized.cost(wrong_start, start.tolist())


def test_rectangular_instance_more_nodes_than_dims() -> None:
    """num_nodes ≠ num_dims (subsystems are rectangular after subtract)."""
    num_dims, num_nodes = 6, 9
    rng = np.random.default_rng(23)
    flat = [rng.random(2**num_dims).astype(np.float32) for _ in range(num_nodes)]
    start = rng.integers(0, 2, size=num_dims).astype(np.int8)
    end = (1 - start).astype(np.int8)

    legacy = LegacyCostTable(flat, start, end)
    vectorized = CostTable(flat, start, end)

    powers = 1 << np.arange(num_dims, dtype=np.int64)
    for (_, state), cost in legacy.transition_table.items():
        row = vectorized.table[int(np.dot(np.array(state), powers))]
        assert np.array_equal(row, np.asarray(cost, dtype=np.float32))
    assert vectorized.candidate_bipartitions() == legacy.candidate_bipartitions()
