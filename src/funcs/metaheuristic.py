"""Shared metaheuristic engine for k-partition search (optional baselines).

The official specification lists metaheuristics (Genetic Algorithm, Simulated
Annealing, Tabu Search) as an *optional comparative* family of strategies
(``docs/Proyecto_KQMIP.md`` §portafolio). They all search the same space as the
core strategies — the strict k-partitions of the subsystem's atoms — and are
scored with the *same* loss ``delta_k``, so they are directly comparable in the
evaluation grid.

Solution encoding
-----------------
A candidate is a label vector ``labels`` of length ``a = |F| + |M|`` (future
atoms first, present atoms last); ``labels[i] ∈ {0..k-1}`` is the block that atom
``i`` belongs to. Decoding splits the vector by layer into paired blocks
``(F_b, M_b)`` and builds a validated :class:`KPartition`. A candidate is
*feasible* iff every one of the ``k`` blocks is non-vacuous (strict semantics,
doc §2.1); infeasible candidates are repaired so the search stays in the feasible
region.

Determinism
-----------
Every search takes an explicit ``numpy.random.Generator`` (seeded from
``application.numpy_seed`` by the strategy), so runs are reproducible.
``delta_k`` evaluations are memoized per search because they dominate the cost.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from src.funcs.emd import delta_k
from src.models.core.partition import KPartition
from src.models.core.system import System


@dataclass
class SearchResult:
    """Outcome of a metaheuristic search."""

    partition: KPartition
    loss: float
    distribution: NDArray[np.float32]
    evaluations: int


def _decode(
    labels: NDArray[np.intp],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
) -> KPartition | None:
    """Build a :class:`KPartition` from a label vector, or ``None`` if infeasible."""
    n_future = len(future_universe)
    blocks: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for block in range(k):
        future_block = tuple(
            future_universe[i] for i in range(n_future) if labels[i] == block
        )
        present_block = tuple(
            present_universe[j] for j in range(len(present_universe))
            if labels[n_future + j] == block
        )
        blocks.append((future_block, present_block))
    try:
        return KPartition.from_blocks(
            blocks=blocks,
            future_universe=future_universe,
            present_universe=present_universe,
        )
    except ValueError:
        # A vacuous block (or any validation failure) means infeasible.
        return None


def _repair(labels: NDArray[np.intp], k: int, rng: np.random.Generator) -> NDArray[np.intp]:
    """Make ``labels`` surjective onto ``{0..k-1}`` (every block non-empty).

    For each empty block, move one atom from a block that currently owns more
    than one atom. This guarantees strict feasibility while changing as few
    assignments as possible.
    """
    labels = labels.copy()
    counts = np.bincount(labels, minlength=k)
    empty = [b for b in range(k) if counts[b] == 0]
    for block in empty:
        # Pick a donor block with a surplus and a random atom from it.
        donors = np.flatnonzero(counts > 1)
        donor = int(rng.choice(donors))
        atom_pool = np.flatnonzero(labels == donor)
        atom = int(rng.choice(atom_pool))
        labels[atom] = block
        counts[donor] -= 1
        counts[block] += 1
    return labels


def _random_solution(a: int, k: int, rng: np.random.Generator) -> NDArray[np.intp]:
    """Return a feasible random label vector of length ``a`` over ``k`` blocks."""
    labels = rng.integers(0, k, size=a, dtype=np.intp)
    # Seed each block with one distinct atom to guarantee surjectivity, then
    # repair any remaining empties (cheap and keeps the rest random).
    seed_atoms = rng.permutation(a)[:k]
    for block, atom in enumerate(seed_atoms):
        labels[atom] = block
    return _repair(labels, k, rng)


class _Evaluator:
    """Memoized ``delta_k`` scorer over label vectors (lower is better)."""

    def __init__(
        self,
        subsystem: System,
        baseline: NDArray[np.float32],
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
        k: int,
    ) -> None:
        self.subsystem = subsystem
        self.baseline = baseline
        self.future_universe = future_universe
        self.present_universe = present_universe
        self.k = k
        self._cache: dict[tuple[int, ...], tuple[float, NDArray[np.float32] | None, KPartition | None]] = {}
        self.evaluations = 0

    def score(
        self, labels: NDArray[np.intp]
    ) -> tuple[float, NDArray[np.float32] | None, KPartition | None]:
        """Return ``(loss, distribution, partition)``; ``inf`` if infeasible."""
        key = tuple(int(x) for x in labels)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        partition = _decode(labels, self.future_universe, self.present_universe, self.k)
        if partition is None:
            result: tuple[float, NDArray[np.float32] | None, KPartition | None] = (
                float("inf"), None, None,
            )
        else:
            loss, distribution = delta_k(
                self.subsystem, partition, baseline_distribution=self.baseline
            )
            self.evaluations += 1
            result = (float(loss), distribution, partition)
        self._cache[key] = result
        return result


def _to_result(
    labels: NDArray[np.intp], evaluator: _Evaluator
) -> SearchResult:
    """Wrap the best label vector into a :class:`SearchResult` (must be feasible)."""
    loss, distribution, partition = evaluator.score(labels)
    if partition is None or distribution is None:
        raise RuntimeError("metaheuristic ended on an infeasible solution (bug in repair).")
    return SearchResult(partition, loss, distribution, evaluator.evaluations)


def genetic_search(
    subsystem: System,
    baseline: NDArray[np.float32],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
    rng: np.random.Generator,
    *,
    population_size: int = 30,
    generations: int = 40,
    mutation_rate: float = 0.2,
    tournament: int = 3,
) -> SearchResult:
    """Genetic Algorithm over label vectors (uniform crossover + relabel mutation)."""
    a = len(future_universe) + len(present_universe)
    evaluator = _Evaluator(subsystem, baseline, future_universe, present_universe, k)

    population = [_random_solution(a, k, rng) for _ in range(population_size)]
    fitness = [evaluator.score(ind)[0] for ind in population]
    best_idx = int(np.argmin(fitness))
    best = population[best_idx].copy()
    best_loss = fitness[best_idx]

    def _select() -> NDArray[np.intp]:
        contenders = rng.integers(0, population_size, size=tournament)
        winner = min(contenders, key=lambda i: fitness[i])
        return population[winner]

    for _ in range(generations):
        new_population: list[NDArray[np.intp]] = [best.copy()]  # elitism
        while len(new_population) < population_size:
            parent_a, parent_b = _select(), _select()
            mask = rng.random(a) < 0.5
            child = np.where(mask, parent_a, parent_b).astype(np.intp)
            if rng.random() < mutation_rate:
                atom = int(rng.integers(0, a))
                child[atom] = int(rng.integers(0, k))
            child = _repair(child, k, rng)
            new_population.append(child)
        population = new_population
        fitness = [evaluator.score(ind)[0] for ind in population]
        gen_best = int(np.argmin(fitness))
        if fitness[gen_best] < best_loss:
            best_loss = fitness[gen_best]
            best = population[gen_best].copy()

    return _to_result(best, evaluator)


def simulated_annealing_search(
    subsystem: System,
    baseline: NDArray[np.float32],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
    rng: np.random.Generator,
    *,
    iterations: int = 1500,
    initial_temp: float = 1.0,
    cooling: float = 0.995,
) -> SearchResult:
    """Simulated Annealing with ``delta_k`` as the energy to minimize."""
    a = len(future_universe) + len(present_universe)
    evaluator = _Evaluator(subsystem, baseline, future_universe, present_universe, k)

    current = _random_solution(a, k, rng)
    current_loss = evaluator.score(current)[0]
    best, best_loss = current.copy(), current_loss
    temp = initial_temp

    for _ in range(iterations):
        neighbor = _neighbor(current, k, rng)
        neighbor_loss = evaluator.score(neighbor)[0]
        delta = neighbor_loss - current_loss
        # Accept improvements always; worse moves with Boltzmann probability.
        if delta < 0 or (temp > 1e-9 and rng.random() < np.exp(-delta / temp)):
            current, current_loss = neighbor, neighbor_loss
            if current_loss < best_loss:
                best, best_loss = current.copy(), current_loss
        temp *= cooling

    return _to_result(best, evaluator)


def tabu_search(
    subsystem: System,
    baseline: NDArray[np.float32],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
    rng: np.random.Generator,
    *,
    iterations: int = 200,
    neighbors_per_step: int = 20,
    tenure: int = 10,
) -> SearchResult:
    """Tabu Search: best non-tabu neighbor each step, with a move tabu list."""
    a = len(future_universe) + len(present_universe)
    evaluator = _Evaluator(subsystem, baseline, future_universe, present_universe, k)

    current = _random_solution(a, k, rng)
    current_loss = evaluator.score(current)[0]
    best, best_loss = current.copy(), current_loss
    tabu: dict[tuple[int, int], int] = {}

    for step in range(iterations):
        best_neighbor: NDArray[np.intp] | None = None
        best_neighbor_loss = float("inf")
        best_move: tuple[int, int] | None = None
        for _ in range(neighbors_per_step):
            atom = int(rng.integers(0, a))
            new_block = int(rng.integers(0, k))
            if new_block == current[atom]:
                continue
            move = (atom, new_block)
            candidate = current.copy()
            candidate[atom] = new_block
            candidate = _repair(candidate, k, rng)
            loss = evaluator.score(candidate)[0]
            is_tabu = tabu.get(move, 0) > step
            # Aspiration: a tabu move is allowed if it beats the global best.
            if is_tabu and loss >= best_loss:
                continue
            if loss < best_neighbor_loss:
                best_neighbor_loss = loss
                best_neighbor = candidate
                best_move = move
        if best_neighbor is None:
            break
        current, current_loss = best_neighbor, best_neighbor_loss
        if best_move is not None:
            tabu[best_move] = step + tenure
        if current_loss < best_loss:
            best, best_loss = current.copy(), current_loss

    return _to_result(best, evaluator)


def _neighbor(labels: NDArray[np.intp], k: int, rng: np.random.Generator) -> NDArray[np.intp]:
    """Return a feasible neighbor by relabeling one atom (with repair)."""
    neighbor = labels.copy()
    atom = int(rng.integers(0, labels.size))
    neighbor[atom] = int(rng.integers(0, k))
    return _repair(neighbor, k, rng)
