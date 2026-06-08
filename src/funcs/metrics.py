"""Evaluation metrics for the k-partition strategies (Phase 7).

These quantify how a strategy's k-partition compares to the exact ground truth
(``ExhaustiveK``) and to other strategies, for the official evaluation grid:

- **exact-hit rate** — did the strategy reach the global k-MIP loss?
- **relative Φ error** — how far its loss is from the exact loss.
- **Jaccard partition distance** — how structurally different two partitions are
  (pair-counting over the atom co-assignment).
- **speedup** — runtime ratio against a baseline (e.g. the exact search).

The metrics take ``KPartition`` objects / scalar losses, never the formatted
partition strings, so they are exact and parser-free.
"""

import numpy as np

from src.models.core.partition import KPartition

# Default tolerance for treating two losses as equal (the grid reports ~6 dp).
LOSS_TOL: float = 1e-6


def is_exact_hit(strategy_loss: float, exact_loss: float, tol: float = LOSS_TOL) -> bool:
    """True if ``strategy_loss`` equals the exact ground-truth loss within ``tol``.

    A heuristic loss can never beat the exact optimum, so this is effectively
    ``strategy_loss <= exact_loss + tol``.
    """
    return strategy_loss <= exact_loss + tol


def relative_phi_error(strategy_loss: float, exact_loss: float) -> float:
    """Relative error of the strategy loss vs the exact loss.

    Falls back to the absolute error when the exact loss is ~0 (the system is
    perfectly separable), since a relative error is undefined there.
    """
    if abs(exact_loss) <= LOSS_TOL:
        return abs(strategy_loss - exact_loss)
    return abs(strategy_loss - exact_loss) / abs(exact_loss)


def _atom_labels(partition: KPartition) -> dict[tuple[str, int], int]:
    """Map each atom (future/present node) to the index of its block."""
    labels: dict[tuple[str, int], int] = {}
    for block_index, (purview, mechanism) in enumerate(partition.signature):
        for future_index in purview:
            labels[("F", int(future_index))] = block_index
        for present_index in mechanism:
            labels[("P", int(present_index))] = block_index
    return labels


def jaccard_partition_distance(part_a: KPartition, part_b: KPartition) -> float:
    """Pair-counting Jaccard distance between two partitions in ``[0, 1]``.

    Considers every unordered pair of atoms and whether the two partitions put
    them in the same block. With ``S`` = pairs together in both and ``D`` =
    pairs together in at least one, the similarity is ``S / D`` (1.0 when the
    partitions are identical) and the distance is ``1 - S / D``. Returns 0.0
    when neither partition groups any pair (both fully singleton).
    """
    labels_a = _atom_labels(part_a)
    labels_b = _atom_labels(part_b)
    atoms = sorted(set(labels_a) & set(labels_b))

    together_both = 0
    together_either = 0
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            same_a = labels_a[atoms[i]] == labels_a[atoms[j]]
            same_b = labels_b[atoms[i]] == labels_b[atoms[j]]
            if same_a or same_b:
                together_either += 1
                if same_a and same_b:
                    together_both += 1

    if together_either == 0:
        return 0.0
    return 1.0 - together_both / together_either


def speedup(baseline_time: float, strategy_time: float) -> float:
    """Speedup of ``strategy_time`` relative to ``baseline_time`` (×)."""
    if strategy_time <= 0:
        return float("inf")
    return baseline_time / strategy_time


def exact_hit_rate(strategy_losses: list[float], exact_losses: list[float]) -> float:
    """Fraction of cases where the strategy reached the exact optimum."""
    if not strategy_losses:
        return 0.0
    hits = sum(
        is_exact_hit(s, e) for s, e in zip(strategy_losses, exact_losses, strict=True)
    )
    return hits / len(strategy_losses)


def scalability_slope(sizes: list[int], times: list[float]) -> float:
    """Empirical exponent ``p`` of ``time ~ size^p`` via a log-log fit.

    Useful to summarize how a strategy scales with ``n`` (or ``k``). Returns
    ``nan`` when fewer than two positive samples are available.
    """
    pairs = [(s, t) for s, t in zip(sizes, times, strict=True) if s > 0 and t > 0]
    if len(pairs) < 2:
        return float("nan")
    log_sizes = np.log(np.array([s for s, _ in pairs], dtype=np.float64))
    log_times = np.log(np.array([t for _, t in pairs], dtype=np.float64))
    slope, _intercept = np.polyfit(log_sizes, log_times, 1)
    return float(slope)
