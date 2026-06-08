"""Cross-validation for the metaheuristic strategies (GA / SA / Tabu).

These are optional comparative baselines: they search the strict k-partition
space and are scored with ``delta_k``, so their loss must be a valid upper bound
on the exact ground truth and they must be reproducible under a fixed seed.
"""

import contextlib
import io

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.controllers.strategies.metaheuristics import AnnealingSIA, GeneticSIA, TabuSIA
from src.models.base.application import application

STRATEGIES = [GeneticSIA, AnnealingSIA, TabuSIA]


def _run(net: str, strategy_cls, **kwargs):
    """Run a strategy on the full subsystem of ``net``."""
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return strategy_cls(tpm, state, **kwargs).apply_strategy(full, full, full)


@pytest.mark.parametrize("strategy_cls", STRATEGIES)
@pytest.mark.parametrize("net", ["N3A", "N4A", "N5B"])
def test_metaheuristic_not_better_than_exact(strategy_cls, net: str) -> None:
    """A heuristic δ_k is an upper bound on the exact k-MIP: meta ≥ exact."""
    exact = _run(net, ExhaustiveK, k=3)
    meta = _run(net, strategy_cls, k=3)
    assert meta.loss >= exact.loss - 1e-9


@pytest.mark.parametrize("strategy_cls", STRATEGIES)
@pytest.mark.parametrize("net", ["N3A", "N4A"])
def test_metaheuristic_finds_exact_on_small(strategy_cls, net: str) -> None:
    """On tiny systems the search should reach the exact optimum."""
    exact = _run(net, ExhaustiveK, k=3)
    meta = _run(net, strategy_cls, k=3)
    assert meta.loss == pytest.approx(exact.loss, abs=1e-4)


@pytest.mark.parametrize("strategy_cls", STRATEGIES)
def test_metaheuristic_is_deterministic(strategy_cls) -> None:
    """Same seed -> identical loss and partition (reproducibility)."""
    first = _run("N4A", strategy_cls, k=3)
    second = _run("N4A", strategy_cls, k=3)
    assert first.loss == pytest.approx(second.loss, abs=1e-12)
    assert first.partition == second.partition


@pytest.mark.parametrize("strategy_cls", STRATEGIES)
def test_metaheuristic_produces_strict_kpartition(strategy_cls) -> None:
    """Result must be a genuine strict k-partition (no fully empty block)."""
    meta = _run("N5B", strategy_cls, k=3)
    assert "∅ | ∅" not in meta.partition
