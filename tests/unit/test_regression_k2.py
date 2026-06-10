import pytest

from src.controllers.strategies.force import BruteForce
from src.controllers.strategies.geometric import GeometricSIA
from tests.fixtures.golden_k2 import NETS, ORACLE_LOSS
from tests.helpers import run_strategy


@pytest.mark.parametrize("net", NETS)
def test_brute_force_equals_geometric(net):
    bf = run_strategy(net, BruteForce)
    geo = run_strategy(net, GeometricSIA)
    assert bf.loss == pytest.approx(geo.loss, abs=1e-9)


@pytest.mark.parametrize("net", NETS)
def test_brute_force_matches_oracle_golden(net):
    bf = run_strategy(net, BruteForce)
    assert bf.loss == pytest.approx(ORACLE_LOSS[net], abs=1e-4)


@pytest.mark.parametrize("net", NETS)
def test_geometric_matches_oracle_golden(net):
    geo = run_strategy(net, GeometricSIA)
    assert geo.loss == pytest.approx(ORACLE_LOSS[net], abs=1e-4)
