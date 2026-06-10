"""Evaluation metrics for the k-partition strategies."""

import numpy as np

from src.models.core.partition import KPartition

LOSS_TOL: float = 1e-6


def is_exact_hit(
    strategy_loss: float, exact_loss: float, tol: float = LOSS_TOL
) -> bool:
    """
    Whether the strategy loss is close enough to the exact loss to be considered a hit.
    """
    return strategy_loss <= exact_loss + tol


def relative_phi_error(strategy_loss: float, exact_loss: float) -> float:
    """
    Relative error of the strategy loss compared to the exact loss.
    If the exact loss is close to zero, returns the absolute error instead.
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
    """Distance between two partitions in the style of clustering evaluation metrics.
    Counts how many pairs of atoms are together in both partitions vs together in either partition.
    Returns a value between 0.0 (identical partitions) and 1.0 (completely different partitions).
    """
    labels_a = _atom_labels(part_a)
    labels_b = _atom_labels(part_b)
    atoms = sorted(set(labels_a) & set(labels_b))

    together_both = 0
    together_either = 0
    for k, v in enumerate(atoms):
        for j in range(k + 1, len(atoms)):
            same_a = labels_a[v] == labels_a[atoms[j]]
            same_b = labels_b[v] == labels_b[atoms[j]]
            if same_a or same_b:
                together_either += 1
                if same_a and same_b:
                    together_both += 1

    if together_either == 0:
        return 0.0
    return 1.0 - together_both / together_either


def speedup(baseline_time: float, strategy_time: float) -> float:
    """Speedup of (strategy_time) relative to (baseline_time).
    Returns a positive number where higher is better,
    and infinity if the strategy is faster than any measurable time.
    """
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
    """Estimated slope of the log-log plot of (times) vs (sizes).
    A slope of 1.0 suggests linear scaling, 2.0 suggests quadratic, etc.
    Returns NaN if there are fewer than 2 valid (size, time) pairs.
    """
    pairs = [(s, t) for s, t in zip(sizes, times, strict=True) if s > 0 and t > 0]
    if len(pairs) < 2:
        return float("nan")
    log_sizes = np.log(np.array([s for s, _ in pairs], dtype=np.float64))
    log_times = np.log(np.array([t for _, t in pairs], dtype=np.float64))
    slope, _ = np.polyfit(log_sizes, log_times, 1)
    return float(slope)
