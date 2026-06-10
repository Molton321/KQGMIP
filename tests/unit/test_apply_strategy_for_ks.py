"""Equality tests for the shared-k entry point (FASE 11).

``apply_strategy_for_ks`` must return, for every requested k, exactly the same
partition and loss as an independent ``apply_strategy`` run with that k — the
only difference is that the expensive preparation (cost table / Queyranne
sequence) is computed once and reused, as the official cost-table spec
requires ("computed once per system ... independently of k").
"""

import contextlib
import io

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.kqnodes import KQNodes
from src.models.base.application import application

NETS = ["N5A", "N6A"]
KS = (2, 3, 4, 5)


def _load(net: str):
    """Return ``(tpm, state, full_mask)`` for the full subsystem of ``net``."""
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    return Manager(state).load_network(), state, "1" * n


@pytest.mark.parametrize("strategy_cls", [KGeoMIP, KQNodes])
@pytest.mark.parametrize("net", NETS)
def test_for_ks_matches_individual_runs(strategy_cls, net: str) -> None:
    """Shared-prep solutions must equal per-k independent solutions exactly."""
    tpm, state, full = _load(net)

    with contextlib.redirect_stdout(io.StringIO()):
        shared = strategy_cls(tpm, state, k=2).apply_strategy_for_ks(full, full, full, KS)

    assert tuple(shared) == KS
    for k in KS:
        with contextlib.redirect_stdout(io.StringIO()):
            individual = strategy_cls(tpm, state, k=k).apply_strategy(full, full, full)
        assert shared[k].loss == individual.loss, (net, k)
        assert shared[k].partition == individual.partition, (net, k)


@pytest.mark.parametrize("strategy_cls", [KGeoMIP, KQNodes])
def test_for_ks_rejects_invalid_k(strategy_cls) -> None:
    """k < 2 must raise, matching the single-k contract."""
    tpm, state, full = _load("N5A")
    with pytest.raises(ValueError):
        strategy_cls(tpm, state, k=2).apply_strategy_for_ks(full, full, full, (1, 3))


@pytest.mark.parametrize("strategy_cls", [KGeoMIP, KQNodes])
def test_for_ks_deduplicates_ks(strategy_cls) -> None:
    """Repeated k values collapse to a single refinement."""
    tpm, state, full = _load("N5A")
    with contextlib.redirect_stdout(io.StringIO()):
        solutions = strategy_cls(tpm, state, k=2).apply_strategy_for_ks(
            full, full, full, (3, 3, 2)
        )
    assert tuple(solutions) == (3, 2)
