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
def test_exactk_k3_is_genuine_and_monotone(net: str) -> None:
    """Strict k-partitions (doc §2.1): k=3 is a genuine 3-way cut.

    Under the EMD-effect δ with product reconstruction, a coarser partition is
    never worse than a finer one, so the optimal genuine 3-way cut has δ₃ ≥ δ₂
    (it cannot degenerate to a bipartition by padding with empty blocks). The
    returned partition must therefore contain exactly 3 non-vacuous blocks.
    """
    solution_k2 = _run_exact(net, k=2)
    solution_k3 = _run_exact(net, k=3)

    # Monotone increasing: a genuine 3-way cut cannot beat the best bipartition.
    assert solution_k3.loss >= solution_k2.loss - 1e-9
    # No degenerate (empty) block: the partition is a true 3-way split.
    assert "∅ | ∅" not in solution_k3.partition
