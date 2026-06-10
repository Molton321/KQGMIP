"""Shared metaheuristic engine for k-partition search (optional baselines)."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from src.constants.metaheuristics import (
    ANNEALING_COOLING,
    ANNEALING_INITIAL_TEMP,
    ANNEALING_ITERATIONS,
    GENETIC_GENERATIONS,
    GENETIC_MUTATION_RATE,
    GENETIC_POPULATION_SIZE,
    GENETIC_TOURNAMENT,
    TABU_ITERATIONS,
    TABU_NEIGHBORS_PER_STEP,
    TABU_TENURE,
)
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
    n_future = len(future_universe)
    blocks: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for block in range(k):
        future_block = tuple(
            future_universe[i] for i in range(n_future) if labels[i] == block
        )
        present_block = tuple(
            present_universe[j]
            for j in range(len(present_universe))
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
        return None


def _repair(
    labels: NDArray[np.intp], k: int, rng: np.random.Generator
) -> NDArray[np.intp]:
    """Make (labels) surjective onto {0..k-1} (every block non-empty).
    For each empty block, move one atom from a block that currently owns more
    than one atom. This guarantees strict feasibility while changing as few
    assignments as possible.
    """
    labels = labels.copy()
    counts = np.bincount(labels, minlength=k)
    empty = [b for b in range(k) if counts[b] == 0]
    for block in empty:
        donors = np.flatnonzero(counts > 1)
        donor = int(rng.choice(donors))
        atom_pool = np.flatnonzero(labels == donor)
        atom = int(rng.choice(atom_pool))
        labels[atom] = block
        counts[donor] -= 1
        counts[block] += 1
    return labels


def _random_solution(a: int, k: int, rng: np.random.Generator) -> NDArray[np.intp]:
    """Return a feasible random label vector of length (a) with (k) blocks.
    Each block is seeded with one distinct atom to guarantee surjectivity, then
    any remaining empties are repaired (cheap, and keeps the rest random).
    """
    labels = rng.integers(0, k, size=a, dtype=np.intp)
    seed_atoms = rng.permutation(a)[:k]
    for block, atom in enumerate(seed_atoms):
        labels[atom] = block
    return _repair(labels, k, rng)


class _Evaluator:
    """Memoized (delta_k) scorer over label vectors (lower is better)."""

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
        self._cache: dict[
            tuple[int, ...], tuple[float, NDArray[np.float32] | None, KPartition | None]
        ] = {}
        self.evaluations = 0

    def score(
        self, labels: NDArray[np.intp]
    ) -> tuple[float, NDArray[np.float32] | None, KPartition | None]:
        key = tuple(int(x) for x in labels)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        partition = _decode(labels, self.future_universe, self.present_universe, self.k)
        if partition is None:
            result: tuple[float, NDArray[np.float32] | None, KPartition | None] = (
                float("inf"),
                None,
                None,
            )
        else:
            loss, distribution = delta_k(
                self.subsystem, partition, baseline_distribution=self.baseline
            )
            self.evaluations += 1
            result = (float(loss), distribution, partition)
        self._cache[key] = result
        return result


def _to_result(labels: NDArray[np.intp], evaluator: _Evaluator) -> SearchResult:
    """Wrap the best label vector into a class (SearchResult) (must be feasible)."""
    loss, distribution, partition = evaluator.score(labels)
    if partition is None or distribution is None:
        raise RuntimeError(
            "metaheuristic ended on an infeasible solution (bug in repair)."
        )
    return SearchResult(partition, loss, distribution, evaluator.evaluations)


def genetic_search(
    subsystem: System,
    baseline: NDArray[np.float32],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
    rng: np.random.Generator,
    *,
    population_size: int = GENETIC_POPULATION_SIZE,
    generations: int = GENETIC_GENERATIONS,
    mutation_rate: float = GENETIC_MUTATION_RATE,
    tournament: int = GENETIC_TOURNAMENT,
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
        new_population: list[NDArray[np.intp]] = [best.copy()]
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
    iterations: int = ANNEALING_ITERATIONS,
    initial_temp: float = ANNEALING_INITIAL_TEMP,
    cooling: float = ANNEALING_COOLING,
) -> SearchResult:
    """Simulated Annealing with (delta_k) as the energy to minimize."""
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
    iterations: int = TABU_ITERATIONS,
    neighbors_per_step: int = TABU_NEIGHBORS_PER_STEP,
    tenure: int = TABU_TENURE,
) -> SearchResult:
    """Tabu Search best non-tabu neighbor each step, with a move tabu list.
    Aspiration is applied: a tabu move is still allowed when it improves on the
    global best loss.
    """
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


def _neighbor(
    labels: NDArray[np.intp], k: int, rng: np.random.Generator
) -> NDArray[np.intp]:
    """Return a feasible neighbor by relabeling one atom (with repair)."""
    neighbor = labels.copy()
    atom = int(rng.integers(0, labels.size))
    neighbor[atom] = int(rng.integers(0, k))
    return _repair(neighbor, k, rng)
