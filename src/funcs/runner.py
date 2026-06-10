"""Strategy registry and a headless analysis runner for the UI/CLI to call.
This module defines the available strategies and their constructors,
as well as a common interface for running an analysis and returning its results
in a structured way.
"""

import contextlib
import importlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.controllers.manager import Manager
from src.controllers.strategies.clustering import ClusteringSIA
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.kqnodes import KQNodes
from src.controllers.strategies.metaheuristics import AnnealingSIA, GeneticSIA, TabuSIA
from src.models.base.application import application
from src.models.core.partition import KPartition
from src.models.core.solution import Solution

StrategyBuilder = Callable[[np.ndarray, str, int, str], Any]
"""A strategy constructor: (tpm, state, k, method) -> SIA instance."""

STRATEGY_BUILDERS: dict[str, StrategyBuilder] = {
    "KGeoMIP": lambda tpm, s, k, method: KGeoMIP(tpm, s, k=k),
    "KQNodes": lambda tpm, s, k, method: KQNodes(tpm, s, k=k),
    "Clustering": lambda tpm, s, k, method: ClusteringSIA(tpm, s, k=k, method=method),
    "Genetic": lambda tpm, s, k, method: GeneticSIA(tpm, s, k=k),
    "Annealing": lambda tpm, s, k, method: AnnealingSIA(tpm, s, k=k),
    "Tabu": lambda tpm, s, k, method: TabuSIA(tpm, s, k=k),
    "ExhaustiveK": lambda tpm, s, k, method: ExhaustiveK(tpm, s, k=k, parallel=True),
}

_LEGACY_STRATEGIES: dict[str, tuple[str, str]] = {
    "BruteForce": ("force", "BruteForce"),
    "GeometricSIA": ("geometric", "GeometricSIA"),
    "QNodes": ("q_nodes", "QNodes"),
    "Phi": ("phi", "Phi"),
}

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
    """Bundle returned by :func:run_analysis for the UI/CLI to render."""

    solution: Solution
    partition: KPartition | None
    strategy: str
    k: int


def resolve_strategy(name: str) -> str:
    """Return the canonical strategy key for a user-typed name (case-insensitive).
    Raises KeyError if the name is not recognized."""
    lookup = {key.lower(): key for key in STRATEGY_BUILDERS}
    lookup.update({key.lower(): key for key in _LEGACY_STRATEGIES})
    lookup["exhaustive"] = "ExhaustiveK"
    lookup["geometric"] = "GeometricSIA"
    canonical = lookup.get(name.lower())
    if canonical is None:
        raise KeyError(f"Estrategia desconocida: {name!r}. Opciones: {sorted(lookup)}")
    return canonical


def build_strategy(name: str, tpm: np.ndarray, state: str, k: int, method: str) -> Any:
    """Construct a strategy instance by name (the one place that does so)."""
    canonical = resolve_strategy(name)
    if canonical in STRATEGY_BUILDERS:
        return STRATEGY_BUILDERS[canonical](tpm, state, k, method)

    module, class_name = _LEGACY_STRATEGIES[canonical]
    strategy_cls = getattr(
        importlib.import_module(f"src.controllers.strategies.{module}"), class_name
    )
    return strategy_cls(tpm, state)


def parse_net_label(net: str) -> tuple[int, str, str]:
    """Parse a net label like "N10A" into its number of nodes, page, and full state."""
    n = int(net[1:-1])
    return n, net[-1], "1" * n


def available_samples(base: Path) -> list[str]:
    """List the available sample networks in a directory, by their net label (e.g. "N10A")."""
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
    """Run one strategy end-to-end and return its solution and partition."""
    canonical = resolve_strategy(strategy)
    full = "1" * len(state)
    condition = condition or full
    purview = purview or full
    mechanism = mechanism or full

    with contextlib.redirect_stdout(io.StringIO()):
        analyzer = build_strategy(canonical, tpm, state, k, method)
        solution = analyzer.apply_strategy(condition, purview, mechanism)

    partition = getattr(analyzer, "best_partition", None)
    return AnalysisResult(
        solution=solution, partition=partition, strategy=canonical, k=k
    )


def load_tpm(state: str, page: str, base_path: Path | None = None) -> np.ndarray:
    """Load the TPM matching len(state) nodes and the given page."""
    application.set_sample_network_page(page)
    manager = (
        Manager(state) if base_path is None else Manager(state, base_path=base_path)
    )
    return manager.load_network()
