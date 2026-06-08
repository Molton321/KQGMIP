"""Strategy registry and a headless analysis runner (Fase 9-C).

A single place that maps a strategy name to its constructor and runs the full
``apply_strategy`` pipeline, returning both the :class:`Solution` and the
underlying :class:`KPartition` (when the strategy exposes one). The Streamlit
web UI and any script can share this instead of duplicating the wiring that
lives in ``main.py``.
"""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.controllers.manager import Manager, _resolve_samples_path
from src.controllers.strategies.clustering import ClusteringSIA
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.kqnodes import KQNodes
from src.controllers.strategies.metaheuristics import AnnealingSIA, GeneticSIA, TabuSIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution

# A strategy constructor: (tpm, state, k, method) -> SIA instance. ``k`` and
# ``method`` are ignored by the strategies that do not use them.
StrategyBuilder = Callable[[np.ndarray, str, int, str], Any]

# Registry of every k-partition strategy exposed to the user (UI dropdown). This
# is the single source of truth for k-strategy construction; the CLI, the web UI
# and the scripts all build strategies through it, never re-importing the classes.
STRATEGY_BUILDERS: dict[str, StrategyBuilder] = {
    "KGeoMIP": lambda tpm, s, k, method: KGeoMIP(tpm, s, k=k),
    "KQNodes": lambda tpm, s, k, method: KQNodes(tpm, s, k=k),
    "Clustering": lambda tpm, s, k, method: ClusteringSIA(tpm, s, k=k, method=method),
    "Genetic": lambda tpm, s, k, method: GeneticSIA(tpm, s, k=k),
    "Annealing": lambda tpm, s, k, method: AnnealingSIA(tpm, s, k=k),
    "Tabu": lambda tpm, s, k, method: TabuSIA(tpm, s, k=k),
    "ExhaustiveK": lambda tpm, s, k, method: ExhaustiveK(tpm, s, k=k),
}

# Legacy bipartition (k=2) strategies — references/baselines, not in the UI list.
# Lazily imported so the common path never loads PyPhi & friends.
def _legacy_builders() -> dict[str, StrategyBuilder]:
    from src.controllers.strategies.force import BruteForce
    from src.controllers.strategies.geometric import GeometricSIA
    from src.controllers.strategies.phi import Phi
    from src.controllers.strategies.q_nodes import QNodes

    return {
        "BruteForce": lambda tpm, s, k, method: BruteForce(tpm, s),
        "GeometricSIA": lambda tpm, s, k, method: GeometricSIA(tpm, s),
        "QNodes": lambda tpm, s, k, method: QNodes(tpm, s),
        "Phi": lambda tpm, s, k, method: Phi(tpm, s),
    }

# Human-readable, one-line description of each strategy (for the UI).
STRATEGY_HELP: dict[str, str] = {
    "KGeoMIP": "Geométrica: cortes sucesivos guiados por la tabla de costos (núcleo).",
    "KQNodes": "Submodular: minimización tipo Queyranne sobre nodos (núcleo).",
    "Clustering": "Baseline determinista: propone la partición por clustering de grafo.",
    "Genetic": "Metaheurística poblacional (algoritmo genético).",
    "Annealing": "Metaheurística de recocido simulado.",
    "Tabu": "Metaheurística de búsqueda tabú.",
    "ExhaustiveK": "Óptimo exacto (Stirling S(2n,k)); sólo para n pequeño.",
}


@dataclass
class AnalysisResult:
    """Bundle returned by :func:`run_analysis` for the UI/CLI to render."""

    solution: Solution
    partition: KPartition | None
    strategy: str
    k: int


def resolve_strategy(name: str) -> str:
    """Return the canonical strategy key for a user-typed name (case-insensitive).

    Accepts the canonical keys and lowercase aliases (e.g. ``"kgeomip"`` ->
    ``"KGeoMIP"``, ``"exhaustive"`` -> ``"ExhaustiveK"``).
    """
    lookup = {key.lower(): key for key in STRATEGY_BUILDERS}
    lookup.update({key.lower(): key for key in _legacy_builders()})
    lookup["exhaustive"] = "ExhaustiveK"  # friendly short aliases
    lookup["geometric"] = "GeometricSIA"
    canonical = lookup.get(name.lower())
    if canonical is None:
        raise KeyError(f"Estrategia desconocida: {name!r}. Opciones: {sorted(lookup)}")
    return canonical


def build_strategy(name: str, tpm: np.ndarray, state: str, k: int, method: str) -> Any:
    """Construct a strategy instance by name (the one place that does so)."""
    builders = {**STRATEGY_BUILDERS, **_legacy_builders()}
    return builders[resolve_strategy(name)](tpm, state, k, method)


def parse_net_label(net: str) -> tuple[int, str, str]:
    """Split a ``N{n}{page}`` label into ``(n, page, state)``.

    The canonical parse used everywhere: ``int(net[1:-1])`` nodes and ``net[-1]``
    page (e.g. ``"N10A"`` -> ``(10, "A", "1111111111")``).
    """
    n = int(net[1:-1])
    return n, net[-1], "1" * n


def available_samples(base_path: Path | None = None) -> list[str]:
    """List the available TPM sample labels (e.g. ``["N10A", "N15A", ...]``).

    Args:
        base_path: directory to scan; defaults to the resolved ``data/samples``.

    Returns:
        Sorted ``N{n}{page}`` labels for every ``*.csv`` sample found.
    """
    base = base_path or _resolve_samples_path()
    if not base.exists():
        return []
    return sorted(p.stem for p in base.glob("N*.csv"))


def run_analysis(
    tpm: np.ndarray,
    state: str,
    strategy: str,
    k: int,
    *,
    method: str = "spectral",
    condition: str | None = None,
    purview: str | None = None,
    mechanism: str | None = None,
) -> AnalysisResult:
    """Run one strategy end-to-end and return its solution and partition.

    Args:
        tpm: the transition probability matrix.
        state: the initial state string (``"1"`` per active node).
        strategy: a key of :data:`STRATEGY_BUILDERS`.
        k: number of blocks (``k >= 2``; ignored by legacy k=2 strategies).
        method: clustering method (``"spectral"`` or ``"kmeans"``); clustering only.
        condition: background-condition mask; defaults to all-active (``state``).
        purview: future-purview mask; defaults to all-active.
        mechanism: present-mechanism mask; defaults to all-active.

    Returns:
        An :class:`AnalysisResult` with the solution and (when available) the
        validated :class:`KPartition`.

    Raises:
        KeyError: if ``strategy`` is not a registered builder.
    """
    canonical = resolve_strategy(strategy)
    full = "1" * len(state)
    condition = condition or full
    purview = purview or full
    mechanism = mechanism or full

    # Strategies print colored progress to stdout; keep the UI/CLI output clean.
    with contextlib.redirect_stdout(io.StringIO()):
        analyzer = build_strategy(canonical, tpm, state, k, method)
        solution = analyzer.apply_strategy(condition, purview, mechanism)

    partition = getattr(analyzer, "best_partition", None)
    return AnalysisResult(solution=solution, partition=partition, strategy=canonical, k=k)


def load_tpm(state: str, page: str, base_path: Path | None = None) -> np.ndarray:
    """Load the TPM matching ``len(state)`` nodes and the given page.

    Args:
        state: initial state string (its length selects ``N{n}``).
        page: sample page letter (``"A"``, ``"B"``, ...).
        base_path: optional override for the samples directory.

    Returns:
        The TPM as a NumPy array.
    """
    from src.models.base.application import application

    application.set_sample_network_page(page)
    manager = Manager(state) if base_path is None else Manager(state, base_path=base_path)
    return manager.load_network()
