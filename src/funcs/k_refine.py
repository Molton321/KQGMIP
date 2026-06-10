"""Shared greedy hierarchical engine for k-partition strategies."""

import numpy as np
from numpy.typing import NDArray

from src.funcs.emd import delta_k
from src.models.core.partition import KPartition
from src.models.core.system import System

Block = tuple[frozenset[int], frozenset[int]]


def greedy_k_partition(
    subsystem: System,
    baseline: NDArray[np.float32],
    cut_pool: list[Block],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
) -> tuple[KPartition, float, NDArray[np.float32]]:
    """Greedily build a k non-vacuous-block partition minimizing (delta_k)."""
    atoms = len(future_universe) + len(present_universe)
    if k > atoms:
        raise ValueError(
            f"k={k} exceeds the {atoms} available atoms "
            f"({len(future_universe)} future + {len(present_universe)} present)."
        )

    blocks: list[Block] = [(frozenset(future_universe), frozenset(present_universe))]
    while len(blocks) < k:
        refined = _best_refinement(
            subsystem, baseline, blocks, cut_pool, future_universe, present_universe
        )
        if refined is None:
            raise RuntimeError(
                f"could not refine into {k} non-vacuous blocks (stuck at {len(blocks)})."
            )
        blocks = refined

    partition = _to_kpartition(blocks, future_universe, present_universe)
    loss, distribution = delta_k(subsystem, partition, baseline_distribution=baseline)
    return partition, float(loss), distribution


def _best_refinement(
    subsystem: System,
    baseline: NDArray[np.float32],
    blocks: list[Block],
    cut_pool: list[Block],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
) -> list[Block] | None:
    """Return the blocks after the single best refinement, or None if no refinement is possible."""
    best_loss = np.inf
    best_blocks: list[Block] | None = None

    for position, (effects_block, present_block) in enumerate(blocks):
        if len(effects_block) + len(present_block) < 2:
            continue

        for cut_effects, cut_present in cut_pool:
            inside: Block = (effects_block & cut_effects, present_block & cut_present)
            outside: Block = (effects_block - cut_effects, present_block - cut_present)

            if not (inside[0] or inside[1]) or not (outside[0] or outside[1]):
                continue

            new_blocks = blocks[:position] + [inside, outside] + blocks[position + 1 :]
            partition = _to_kpartition(new_blocks, future_universe, present_universe)
            loss, _ = delta_k(subsystem, partition, baseline_distribution=baseline)
            if loss < best_loss:
                best_loss = loss
                best_blocks = new_blocks

    return best_blocks


def _to_kpartition(
    blocks: list[Block],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
) -> KPartition:
    """Build a validated (KPartition) from the current working blocks."""
    return KPartition.from_blocks(
        blocks=[
            (tuple(sorted(effects)), tuple(sorted(present)))
            for effects, present in blocks
        ],
        future_universe=future_universe,
        present_universe=present_universe,
    )
