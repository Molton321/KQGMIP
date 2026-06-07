"""Cross-validation for the ExhaustiveK strategy (Phase 2 ground truth)."""

import contextlib
import io

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.models.base.application import application
from tests.fixtures.golden_k2 import NETS, ORACLE_LOSS


def _run_exact(net: str, k: int):
    """Run ExhaustiveK on a small full subsystem for the given network and k."""
    n = int(net[1:-1])
    page = net[-1]
    state = "1" * n

    application.set_sample_network_page(page)
    tpm = Manager(state).load_network()
    full = "1" * n

    with contextlib.redirect_stdout(io.StringIO()):
        return ExhaustiveK(tpm, state, k=k).apply_strategy(full, full, full)


@pytest.mark.parametrize("net", NETS)
def test_exactk_k2_matches_oracle_golden(net: str) -> None:
    """ExhaustiveK(k=2) must reproduce the BruteForce/GeometricSIA golden δ for k=2."""
    solution = _run_exact(net, k=2)
    assert solution.loss == pytest.approx(ORACLE_LOSS[net], abs=1e-4)


@pytest.mark.parametrize("net", ["N2A", "N3A", "N4A"])
def test_exactk_k3_is_leq_oracle_k2(net: str) -> None:
    """Splitting into more blocks can only reduce (or keep) information loss.

    For networks whose optimal k=2 δ is > 0, k=3 must reach at most the same
    value; for networks where the optimal δ is already 0, k=3 must remain 0.
    """
    solution_k3 = _run_exact(net, k=3)
    oracle = ORACLE_LOSS[net]
    assert solution_k3.loss <= oracle + 1e-4
