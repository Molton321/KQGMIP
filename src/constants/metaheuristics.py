"""Tuned hyperparameters for the comparative metaheuristic strategies.

Centralized here so there are no tuning literals scattered in the search
functions (``src/funcs/metaheuristic.py`` reads these as its defaults).

Genetic Algorithm budget was raised from 30/40 to ``60``/``80`` on 2026-06-09:
the evaluation grid showed GA was the weakest strategy, and a direct measurement
against the exact ExhaustiveK optimum on N6A ``k=3`` confirmed the small budget
gave a ~11.5% loss error (1.0625 vs the exact 0.95312) while ``60``/``80`` reaches
the exact optimum (0% error). The larger budget stays well within the runtime
ceiling. The convergence is locked by ``tests/unit/test_metaheuristics.py``.

The Simulated Annealing and Tabu parameters are relocated unchanged; centralizing
them keeps the whole metaheuristic family's tuning in one documented place.
"""

GENETIC_POPULATION_SIZE = 60
"""Number of candidate label vectors carried each generation."""

GENETIC_GENERATIONS = 80
"""Number of generations (selection + crossover + mutation rounds)."""

GENETIC_MUTATION_RATE = 0.2
"""Probability of a single-atom relabel mutation per child."""

GENETIC_TOURNAMENT = 3
"""Tournament size for parent selection."""

ANNEALING_ITERATIONS = 1500
"""Number of proposal steps for Simulated Annealing."""

ANNEALING_INITIAL_TEMP = 1.0
"""Starting temperature for the acceptance schedule."""

ANNEALING_COOLING = 0.995
"""Geometric cooling factor applied each step."""

TABU_ITERATIONS = 200
"""Number of best-neighbor moves for Tabu Search."""

TABU_NEIGHBORS_PER_STEP = 20
"""Neighbors sampled per Tabu step before picking the best non-tabu one."""

TABU_TENURE = 10
"""Number of steps a reversed move stays tabu."""
