"""Cross-validation for the KQNodes strategy (Phase 4, submodular k-partitions)."""

import contextlib
import io

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.controllers.strategies.kqnodes import KQNodes
from src.controllers.strategies.q_nodes import QNodes
from src.models.base.application import application
from tests.fixtures.golden_k2 import NETS, ORACLE_LOSS, QNODES_LOSS


def _run(net: str, strategy_cls, **kwargs):
    """Run a strategy on the full subsystem of ``net``."""
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return strategy_cls(tpm, state, **kwargs).apply_strategy(full, full, full)


@pytest.mark.parametrize("net", NETS)
def test_kqnodes_k2_not_worse_than_qnodes(net: str) -> None:
    """KQNodes(k=2) never does worse than legacy QNodes.

    It searches the same submodular candidate pool but scores each candidate
    with the consistent δ_k (real EMD), so its bipartition loss is an upper
    bound by QNodes' reported loss.
    """
    kq = _run(net, KQNodes, k=2)
    assert kq.loss <= QNODES_LOSS[net] + 1e-9


@pytest.mark.parametrize("net", NETS)
def test_kqnodes_k2_not_below_oracle(net: str) -> None:
    """KQNodes(k=2) is a valid bipartition, so it cannot beat the global optimum."""
    kq = _run(net, KQNodes, k=2)
    assert kq.loss >= ORACLE_LOSS[net] - 1e-9


def test_kqnodes_k2_fixes_qnodes_n3b_defect() -> None:
    """On N3B, consistent δ_k scoring lets KQNodes reach the optimum that the
    legacy QNodes memo missed (0.46875 vs QNodes' suboptimal 0.5)."""
    qn = _run("N3B", QNodes)
    kq = _run("N3B", KQNodes, k=2)
    assert qn.loss == pytest.approx(QNODES_LOSS["N3B"], abs=1e-4)  # 0.5 (legacy defect)
    assert kq.loss == pytest.approx(ORACLE_LOSS["N3B"], abs=1e-4)  # 0.46875 (optimal)
    assert kq.loss < qn.loss


@pytest.mark.parametrize("net", ["N3A", "N3B", "N4A", "N4B", "N5B"])
def test_kqnodes_k3_not_better_than_exact(net: str) -> None:
    """The greedy submodular search cannot beat the exact ground truth:
    ExhaustiveK(k=3) ≤ KQNodes(k=3)."""
    exact = _run(net, ExhaustiveK, k=3)
    kq = _run(net, KQNodes, k=3)
    assert kq.loss >= exact.loss - 1e-9


@pytest.mark.parametrize("net", ["N3A", "N4A", "N5B"])
def test_kqnodes_k3_is_genuine_three_way(net: str) -> None:
    """A strict k=3 partition has three non-vacuous parts (no empty block)."""
    kq = _run(net, KQNodes, k=3)
    assert "∅ | ∅" not in kq.partition
