"""Parallel candidate evaluation: correctness, determinism, seed control (Phase 6)."""

import contextlib
import io

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.funcs.parallel import derive_seeds
from src.models.base.application import application


def _run_exact(net: str, k: int, parallel: bool):
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return ExhaustiveK(tpm, state, k=k, parallel=parallel, n_jobs=2).apply_strategy(
            full, full, full
        )


def test_derive_seeds_is_deterministic() -> None:
    """Seeds spawned from the global seed are reproducible and independent."""
    first = derive_seeds(4)
    second = derive_seeds(4)
    assert first == second
    assert len(set(first)) == 4  # independent (no collisions)


@pytest.mark.parametrize("net, k", [("N3A", 2), ("N4A", 3), ("N5B", 3)])
def test_parallel_matches_sequential(net: str, k: int) -> None:
    """Process-parallel evaluation returns exactly the sequential exact result."""
    sequential = _run_exact(net, k, parallel=False)
    parallel = _run_exact(net, k, parallel=True)
    assert parallel.loss == pytest.approx(sequential.loss, abs=1e-9)
    assert parallel.partition == sequential.partition
