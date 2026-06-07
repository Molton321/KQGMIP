"""Cross-validation for the clustering baseline (Phase 5A)."""

import contextlib
import io

import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.clustering import ClusteringSIA
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.models.base.application import application


def _run(net: str, strategy_cls, **kwargs):
    """Run a strategy on the full subsystem of ``net``."""
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return strategy_cls(tpm, state, **kwargs).apply_strategy(full, full, full)


@pytest.mark.parametrize("net, k", [("N3A", 2), ("N4A", 3), ("N5B", 4)])
def test_clustering_is_deterministic(net: str, k: int) -> None:
    """The baseline must produce identical output across runs (fixed seed)."""
    first = _run(net, ClusteringSIA, k=k)
    second = _run(net, ClusteringSIA, k=k)
    assert first.loss == second.loss
    assert first.partition == second.partition


@pytest.mark.parametrize("net, k", [("N3A", 2), ("N3A", 3), ("N4A", 3), ("N4B", 4)])
def test_clustering_not_better_than_exact(net: str, k: int) -> None:
    """The proposed partition cannot beat the exact ground truth."""
    exact = _run(net, ExhaustiveK, k=k)
    cluster = _run(net, ClusteringSIA, k=k)
    assert cluster.loss >= exact.loss - 1e-9


@pytest.mark.parametrize("net, k", [("N4A", 3), ("N5B", 4)])
def test_clustering_is_genuine_k_way(net: str, k: int) -> None:
    """A strict k-partition has k non-vacuous parts (no empty block).

    The formatted partition prints one ``Bi: …`` line per block, so the line
    count equals the number of blocks.
    """
    cluster = _run(net, ClusteringSIA, k=k)
    assert "∅ | ∅" not in cluster.partition
    assert len(cluster.partition.splitlines()) == k


def test_clustering_rejects_k_greater_than_nodes() -> None:
    """Node-aligned clustering needs k <= n nodes."""
    with pytest.raises(ValueError, match="k <= n"):
        _run("N3A", ClusteringSIA, k=4)


def test_clustering_kmeans_variant_runs() -> None:
    """The simple k-means variant ('Estrategia KM') also yields a valid k-partition."""
    cluster = _run("N4A", ClusteringSIA, k=2, method="kmeans")
    assert isinstance(cluster.loss, float)
    assert len(cluster.partition.splitlines()) == 2
