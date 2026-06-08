"""Metaheuristic k-partition strategies (optional comparative baselines).

Three classic metaheuristics — Genetic Algorithm (:class:`GeneticSIA`),
Simulated Annealing (:class:`AnnealingSIA`) and Tabu Search (:class:`TabuSIA`) —
that search the strict k-partition space and are scored with the same loss
``delta_k`` as the core strategies, so they slot directly into the evaluation
grid. They are listed as an optional comparison family in the official
specification (``docs/Proyecto_KQMIP.md``).

All three share the engine in :mod:`src.funcs.metaheuristic` and differ only in
the search operator. Each is seeded from ``application.numpy_seed`` for
reproducibility (DoD: deterministic results across runs).
"""

import time
from collections.abc import Callable

import numpy as np

from src.constants.base import TYPE_TAG
from src.funcs.format import fmt_kpartition
from src.funcs.metaheuristic import (
    SearchResult,
    genetic_search,
    simulated_annealing_search,
    tabu_search,
)
from src.middlewares.profile import profile
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution


class _MetaheuristicSIA(SIA):
    """Common scaffolding for the metaheuristic strategies.

    Subclasses set :attr:`label` and implement :meth:`_search`, which receives
    the prepared subsystem context and a seeded RNG and returns a
    :class:`SearchResult`.
    """

    label: str = "Metaheuristic"

    def __init__(self, tpm: np.ndarray, initial_state: str, k: int) -> None:
        super().__init__(tpm, initial_state)
        self.logger = SafeLogger(f"{self.label}_strategy")
        self.k = k
        self.best_partition: KPartition | None = None

    def _search(
        self,
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
        rng: np.random.Generator,
    ) -> SearchResult:  # pragma: no cover - overridden
        del future_universe, present_universe, rng
        raise NotImplementedError

    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Search for a low-loss k-partition with the configured metaheuristic."""
        self.sia_prepare_subsystem(condition, purview, mechanism)
        if self.k < 2:
            raise ValueError("k must be >= 2.")

        future_universe = tuple(int(i) for i in self.sia_subsystem.ncube_indices.tolist())
        present_universe = tuple(int(i) for i in self.sia_subsystem.ncube_dims.tolist())
        atoms = len(future_universe) + len(present_universe)
        if self.k > atoms:
            raise ValueError(f"k={self.k} exceeds the {atoms} available atoms.")

        rng = np.random.default_rng(application.numpy_seed)
        self.sia_logger.critic(f"Iniciando búsqueda {self.label}.")
        result = self._search(future_universe, present_universe, rng)
        self.best_partition = result.partition

        return Solution(
            strategy=f"{self.label}(k={self.k})",
            loss=result.loss,
            subsystem_distribution=self.sia_marginal_dists,
            partition_distribution=result.distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(result.partition.signature),
        )

    def _run(
        self,
        search: Callable[..., SearchResult],
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
        rng: np.random.Generator,
    ) -> SearchResult:
        """Invoke a search function with the shared subsystem arguments."""
        return search(
            self.sia_subsystem,
            self.sia_marginal_dists,
            future_universe,
            present_universe,
            self.k,
            rng,
        )


class GeneticSIA(_MetaheuristicSIA):
    """Genetic Algorithm k-partition strategy (uniform crossover + mutation)."""

    label = "Genetic"

    @profile(context={TYPE_TAG: "Genetic_analysis"})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        return super().apply_strategy(condition, purview, mechanism)

    def _search(self, future_universe, present_universe, rng) -> SearchResult:
        return self._run(genetic_search, future_universe, present_universe, rng)


class AnnealingSIA(_MetaheuristicSIA):
    """Simulated Annealing k-partition strategy (δ_k as energy)."""

    label = "Annealing"

    @profile(context={TYPE_TAG: "Annealing_analysis"})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        return super().apply_strategy(condition, purview, mechanism)

    def _search(self, future_universe, present_universe, rng) -> SearchResult:
        return self._run(simulated_annealing_search, future_universe, present_universe, rng)


class TabuSIA(_MetaheuristicSIA):
    """Tabu Search k-partition strategy (best non-tabu neighbor + tabu list)."""

    label = "Tabu"

    @profile(context={TYPE_TAG: "Tabu_analysis"})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        return super().apply_strategy(condition, purview, mechanism)

    def _search(self, future_universe, present_universe, rng) -> SearchResult:
        return self._run(tabu_search, future_universe, present_universe, rng)
