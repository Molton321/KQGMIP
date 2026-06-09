"""Cross-validation for the KGeoMIP strategy (Phase 3, geometric k-partitions)."""

import contextlib
import io
from unittest import mock

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.kgeomip import KGeoMIP
from src.models.base.application import application
from tests.fixtures.golden_k2 import NETS, ORACLE_LOSS


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
def test_kgeomip_k2_matches_oracle_golden(net: str) -> None:
    """KGeoMIP(k=2) must reproduce the GeoMIP/oracle golden δ (doc §109)."""
    solution = _run(net, KGeoMIP, k=2)
    assert solution.loss == pytest.approx(ORACLE_LOSS[net], abs=1e-4)


@pytest.mark.parametrize("net", NETS)
def test_kgeomip_k2_equals_geometric(net: str) -> None:
    """KGeoMIP(k=2) reduces exactly to the legacy GeoMIP bipartition search."""
    geo = _run(net, GeometricSIA)
    kgeo = _run(net, KGeoMIP, k=2)
    assert kgeo.loss == pytest.approx(geo.loss, abs=1e-9)


@pytest.mark.parametrize("net", ["N3A", "N3B", "N4A", "N4B", "N5B"])
def test_kgeomip_k3_not_better_than_exact(net: str) -> None:
    """The greedy geometric search cannot beat the exact ground truth.

    KGeoMIP is a heuristic, so its δ₃ is an upper bound on the exact k-MIP:
    ExhaustiveK(k=3) ≤ KGeoMIP(k=3).
    """
    exact = _run(net, ExhaustiveK, k=3)
    kgeo = _run(net, KGeoMIP, k=3)
    assert kgeo.loss >= exact.loss - 1e-9


@pytest.mark.parametrize("net", ["N3A", "N4A", "N5B"])
def test_kgeomip_k3_is_genuine_three_way(net: str) -> None:
    """A strict k=3 partition has three non-vacuous parts (no empty block)."""
    kgeo = _run(net, KGeoMIP, k=3)
    assert "∅ | ∅" not in kgeo.partition


def test_kgeomip_builds_cost_table_once_per_run() -> None:
    """The expensive transition table T is computed once and reused for all k−1
    cuts within a single analysis (doc §3: 'calcularse una única vez')."""
    from src.funcs.cost_table import CostTable

    n = 4
    application.set_sample_network_page("A")
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n

    with mock.patch("src.controllers.strategies.kgeomip.CostTable", side_effect=CostTable) as spy:
        with contextlib.redirect_stdout(io.StringIO()):
            KGeoMIP(tpm, state, k=4).apply_strategy(full, full, full)

    assert spy.call_count == 1
