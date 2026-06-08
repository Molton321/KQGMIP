"""End-to-end integration tests for the K-QGMIP pipeline.

These exercise the full path a user follows — load a TPM, build a strategy, run
``apply_strategy`` and read the :class:`Solution` — and check cross-strategy
consistency on small systems where the exact ground truth is available.
"""

import contextlib
import io

import numpy as np
import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.clustering import ClusteringSIA
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.kqnodes import KQNodes
from src.controllers.strategies.metaheuristics import AnnealingSIA, GeneticSIA, TabuSIA
from src.models.base.application import application

# Every k-partition strategy exposed to the user (label -> factory).
K_STRATEGIES = {
    "kgeomip": lambda tpm, s: KGeoMIP(tpm, s, k=3),
    "kqnodes": lambda tpm, s: KQNodes(tpm, s, k=3),
    "clustering": lambda tpm, s: ClusteringSIA(tpm, s, k=3, method="spectral"),
    "genetic": lambda tpm, s: GeneticSIA(tpm, s, k=3),
    "annealing": lambda tpm, s: AnnealingSIA(tpm, s, k=3),
    "tabu": lambda tpm, s: TabuSIA(tpm, s, k=3),
}


def _run(net: str, factory):
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return factory(tpm, state).apply_strategy(full, full, full)


@pytest.mark.parametrize("name", list(K_STRATEGIES))
def test_pipeline_produces_valid_solution(name: str) -> None:
    """Each strategy yields a finite, non-negative loss and a partition string."""
    solution = _run("N4A", K_STRATEGIES[name])
    assert np.isfinite(solution.loss)
    assert solution.loss >= -1e-12
    assert solution.partition.strip() != ""
    assert solution.execution_time >= 0.0


@pytest.mark.parametrize("name", list(K_STRATEGIES))
def test_heuristics_bounded_by_exact(name: str) -> None:
    """No heuristic can beat the exact k-MIP ground truth (δ_k ≥ exact)."""
    exact = _run("N4A", lambda tpm, s: ExhaustiveK(tpm, s, k=3))
    solution = _run("N4A", K_STRATEGIES[name])
    assert solution.loss >= exact.loss - 1e-9


def test_k2_regression_kgeomip_equals_geometric() -> None:
    """KGeoMIP(k=2) reproduces the legacy GeoMIP bipartition end-to-end."""
    geo = _run("N5B", lambda tpm, s: GeometricSIA(tpm, s))
    kgeo = _run("N5B", lambda tpm, s: KGeoMIP(tpm, s, k=2))
    assert kgeo.loss == pytest.approx(geo.loss, abs=1e-9)


def test_generate_and_load_roundtrip(tmp_path) -> None:
    """A generated TPM can be loaded back and analyzed (CSV by command)."""
    state = "111"
    manager = Manager(state, base_path=tmp_path)
    application.set_sample_network_page("A")
    with contextlib.redirect_stdout(io.StringIO()):
        filename = manager.generate_network(3, deterministic=True)
    assert (tmp_path / filename).exists()

    tpm = manager.load_network()
    assert tpm.shape == (8, 3)
    with contextlib.redirect_stdout(io.StringIO()):
        solution = KGeoMIP(tpm, state, k=2).apply_strategy("111", "111", "111")
    assert np.isfinite(solution.loss)
