import pytest

from src.controllers.strategies.force import BruteForce
from src.controllers.strategies.q_nodes import QNodes
from tests.fixtures.golden_k2 import NETS, ORACLE_LOSS, QNODES_LOSS, QNODES_SUBOPTIMAL
from tests.helpers import run_strategy


@pytest.mark.triage
@pytest.mark.parametrize("net", NETS)
def test_qnodes_matches_current_golden(net):
    q = run_strategy(net, QNodes)
    assert q.loss == pytest.approx(QNODES_LOSS[net], abs=1e-4)


@pytest.mark.triage
@pytest.mark.parametrize("net", QNODES_SUBOPTIMAL)
def test_qnodes_is_suboptimal_versus_oracle(net):
    q = run_strategy(net, QNodes)
    assert q.loss > ORACLE_LOSS[net] + 1e-4


@pytest.mark.triage
def test_qnodes_defect_rate_is_known():
    defects = 0
    for net in NETS:
        bf = run_strategy(net, BruteForce)
        q = run_strategy(net, QNodes)
        if q.loss > bf.loss + 1e-4:
            defects += 1
    assert defects == len(QNODES_SUBOPTIMAL)
