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

# A k-strategy constructor: (tpm, state, k, method) -> SIA instance.
StrategyBuilder = Callable[[np.ndarray, str, int, str], Any]

# Registry of every k-partition strategy exposed to the user. ``method`` is only
# consulted by the clustering baseline; the rest ignore it.
STRATEGY_BUILDERS: dict[str, StrategyBuilder] = {
    "KGeoMIP": lambda tpm, s, k, method: KGeoMIP(tpm, s, k=k),
    "KQNodes": lambda tpm, s, k, method: KQNodes(tpm, s, k=k),
    "Clustering": lambda tpm, s, k, method: ClusteringSIA(tpm, s, k=k, method=method),
    "Genetic": lambda tpm, s, k, method: GeneticSIA(tpm, s, k=k),
    "Annealing": lambda tpm, s, k, method: AnnealingSIA(tpm, s, k=k),
    "Tabu": lambda tpm, s, k, method: TabuSIA(tpm, s, k=k),
    "ExhaustiveK": lambda tpm, s, k, method: ExhaustiveK(tpm, s, k=k),
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
    if strategy not in STRATEGY_BUILDERS:
        raise KeyError(f"Estrategia desconocida: {strategy!r}")

    full = "1" * len(state)
    condition = condition or full
    purview = purview or full
    mechanism = mechanism or full

    builder = STRATEGY_BUILDERS[strategy]
    # Strategies print colored progress to stdout; keep the UI/CLI output clean.
    with contextlib.redirect_stdout(io.StringIO()):
        analyzer = builder(tpm, state, k, method)
        solution = analyzer.apply_strategy(condition, purview, mechanism)

    partition = getattr(analyzer, "best_partition", None)
    return AnalysisResult(solution=solution, partition=partition, strategy=strategy, k=k)


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
