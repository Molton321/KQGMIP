"""Equality tests for the local marginal evaluation (FASE 11).

``NCube.marginal_value`` and the two ``System`` wrappers must return the same
float32 values as the legacy path (full ``marginalize`` reduction followed by
indexing at the initial state). For the **deterministic 0/1 TPMs the project
runs on** the means are dyadic and the agreement is exact (bit by bit), which
is what keeps Invariante 1 (k=2 reproduction) intact. For arbitrary non-dyadic
float32 data the two paths may differ by the pairwise-summation order of
``np.mean`` — measured at most **1 ulp** (1.19e-07) over every bipartition of
random 3/4/6-node systems — so those cases assert a 2-ulp bound instead.
"""

import contextlib
import io
from itertools import combinations

import numpy as np
import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.q_nodes import QNodes
from src.models.base.application import application
from src.models.core.partition import KPartition
from src.models.core.system import System

ULP_BOUND = 2 * float(np.finfo(np.float32).eps)
"""Tolerance for non-dyadic float32 data (measured worst case: 1 ulp)."""


def _assert_marginals_equal(full: np.ndarray, local: np.ndarray, deterministic: bool, ctx) -> None:
    """Exact equality for dyadic (deterministic) data, 2-ulp bound otherwise."""
    if deterministic:
        assert np.array_equal(full, local), ctx
    else:
        np.testing.assert_allclose(full, local, rtol=0.0, atol=ULP_BOUND, err_msg=str(ctx))


def _random_system(num_nodes: int, seed: int, deterministic: bool) -> System:
    """Build a System over a random (optionally deterministic 0/1) TPM."""
    rng = np.random.default_rng(seed)
    if deterministic:
        tpm = rng.integers(0, 2, size=(2**num_nodes, num_nodes)).astype(np.float32)
    else:
        tpm = rng.random((2**num_nodes, num_nodes)).astype(np.float32)
    state = rng.integers(0, 2, size=num_nodes).astype(np.int8)
    return System(tpm, state)


@pytest.mark.parametrize("num_nodes", [3, 4, 6])
@pytest.mark.parametrize("deterministic", [True, False])
def test_bipartition_local_equals_full_path(num_nodes: int, deterministic: bool) -> None:
    """Local bipartition marginals == bipartition().marginal_distribution(), exactly."""
    system = _random_system(num_nodes, seed=num_nodes, deterministic=deterministic)
    indices = list(range(num_nodes))

    for purview_size in range(num_nodes + 1):
        for purview in combinations(indices, purview_size):
            for mechanism_size in range(num_nodes + 1):
                for mechanism in combinations(indices, mechanism_size):
                    purview_arr = np.array(purview, dtype=np.int8)
                    mechanism_arr = np.array(mechanism, dtype=np.int8)
                    full = system.bipartition(
                        purview_arr, mechanism_arr
                    ).marginal_distribution()
                    local = system.bipartition_marginal_distribution(
                        purview_arr, mechanism_arr
                    )
                    _assert_marginals_equal(full, local, deterministic, (purview, mechanism))


@pytest.mark.parametrize("deterministic", [True, False])
def test_k_partition_local_equals_full_path(deterministic: bool) -> None:
    """Local k-partition marginals == k_partition().marginal_distribution(), exactly."""
    num_nodes = 5
    system = _random_system(num_nodes, seed=11, deterministic=deterministic)
    universe = tuple(range(num_nodes))

    signatures = [
        (((0, 1), (0, 1, 2)), ((2, 3, 4), (3, 4))),
        (((0,), (0,)), ((1, 2), (1, 2)), ((3, 4), (3, 4))),
        (((0, 2, 4), ()), ((1, 3), (0, 1, 2, 3, 4))),
        (((0,), (4,)), ((1,), (3,)), ((2,), (2,)), ((3, 4), (0, 1))),
    ]
    for signature in signatures:
        partition = KPartition.from_blocks(signature, universe, universe)
        full = system.k_partition(partition).marginal_distribution()
        local = system.k_partition_marginal_distribution(partition)
        _assert_marginals_equal(full, local, deterministic, signature)


def test_k_partition_local_validates_universes() -> None:
    """The local variant must reject mismatched universes like k_partition does."""
    system = _random_system(4, seed=7, deterministic=True)
    wrong_universe = (0, 1, 2)
    partition = KPartition.from_blocks(
        (((0, 1), (0, 1)), ((2,), (2,))), wrong_universe, wrong_universe
    )
    with pytest.raises(ValueError):
        system.k_partition_marginal_distribution(partition)


@pytest.mark.parametrize("net", ["N3B", "N5B", "N6A"])
def test_qnodes_end_to_end_keeps_golden_loss(net: str) -> None:
    """QNodes with the local marginal path must reproduce the frozen legacy loss."""
    from tests.fixtures.golden_k2 import QNODES_LOSS

    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        solution = QNodes(tpm, state).apply_strategy(full, full, full)
    assert solution.loss == QNODES_LOSS[net]
