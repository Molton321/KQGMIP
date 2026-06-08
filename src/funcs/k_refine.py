"""Shared greedy hierarchical engine for k-partition strategies.

Both KGeoMIP (geometric) and KQNodes (submodular) build a k-partition the same
way (official doc ``docs/Proyecto_KQMIP.md`` §2.2: a k-partition as k−1
successive bipartitions): starting from the whole subsystem as a single block,
repeatedly split one block with the best available *cut* until k non-vacuous
blocks are reached. The two strategies differ only in **how the cut pool is
produced** (the geometric cost table vs. the submodular Queyranne candidates),
so the refinement loop itself lives here and is reused by both.

A cut and a block are both represented as a pair ``(future_indices,
present_indices)`` of frozensets. Splitting block ``b`` with cut ``c`` yields
``(b ∩ c, b \\ c)``; for the first split (``b`` = whole subsystem) this is just
``c`` and its complement, so the search reduces to the legacy bipartition.
"""

import numpy as np
from numpy.typing import NDArray

from src.funcs.emd import delta_k
from src.models.core.partition import KPartition
from src.models.core.system import System

# A block/cut pairs future (purview) indices with present (mechanism) indices.
# It is non-vacuous when either set is non-empty.
Block = tuple[frozenset[int], frozenset[int]]


def greedy_k_partition(
    subsystem: System,
    baseline: NDArray[np.float32],
    cut_pool: list[Block],
    future_universe: tuple[int, ...],
    present_universe: tuple[int, ...],
    k: int,
) -> tuple[KPartition, float, NDArray[np.float32]]:
    """Greedily build a k non-vacuous-block partition minimizing ``delta_k``.

    Args:
        subsystem: The prepared subsystem to partition.
        baseline: Its marginal distribution (the δ_k reference).
        cut_pool: Candidate cuts proposed by the strategy (geometric/submodular).
        future_universe: All future (purview) indices of the subsystem.
        present_universe: All present (mechanism) indices of the subsystem.
        k: Target number of non-vacuous blocks (k ≥ 2).

    Returns:
        ``(partition, loss, distribution)`` for the resulting k-partition.

    Raises:
        ValueError: if ``k`` exceeds the number of available atoms.
        RuntimeError: if the pool cannot refine the system into k non-vacuous
            blocks.
    """
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
    """Return the blocks after the single best (lowest δ_k) split.

    Tries every (block, cut) pairing that divides a block into two non-vacuous
    sub-blocks, scores the resulting full partition with ``delta_k``, and keeps
    the minimum. The per-step candidate batch is small (~k·|cut_pool|), so the
    scalar ``delta_k`` path is faster here than a batched kernel (measured); the
    batch kernel (``accelerate.batch_effect_emd``) is reserved for large-batch
    consumers. Returns ``None`` if no block can be split into two non-vacuous
    parts with the available cuts.
    """
    best_loss = np.inf
    best_blocks: list[Block] | None = None

    for position, (effects_block, present_block) in enumerate(blocks):
        # A block needs at least two atoms to split into two non-vacuous parts.
        if len(effects_block) + len(present_block) < 2:
            continue

        for cut_effects, cut_present in cut_pool:
            inside: Block = (effects_block & cut_effects, present_block & cut_present)
            outside: Block = (effects_block - cut_effects, present_block - cut_present)

            # Reject splits that leave a fully empty (vacuous) side.
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
    """Build a validated ``KPartition`` from the current working blocks."""
    return KPartition.from_blocks(
        blocks=[(tuple(sorted(effects)), tuple(sorted(present))) for effects, present in blocks],
        future_universe=future_universe,
        present_universe=present_universe,
    )
