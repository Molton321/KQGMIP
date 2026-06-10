import numpy as np
import pytest

from src.models.core.partition import KPartition


def test_kpartition_rejects_mismatched_block_counts() -> None:
    with pytest.raises(ValueError, match="same length"):
        KPartition(
            purview_blocks=((0,), (1,)),
            mechanism_blocks=((0,),),
            future_universe=(0, 1),
            present_universe=(0,),
        )


def test_kpartition_rejects_all_vacuous_partition() -> None:
    with pytest.raises(ValueError, match="non-vacuous"):
        KPartition(
            purview_blocks=(tuple(), tuple()),
            mechanism_blocks=(tuple(), tuple()),
            future_universe=(0,),
            present_universe=(0,),
        )


def test_kpartition_rejects_any_vacuous_block_strict() -> None:
    """Strict semantics (doc §2.1): every one of the k blocks must be non-vacuous.

    A k=3 candidate with a padding (empty, empty) block is rejected so the
    k-partition cannot degenerate to a coarser partition.
    """
    with pytest.raises(ValueError, match="all 3 blocks to be non-vacuous"):
        KPartition(
            purview_blocks=((0,), (1,), tuple()),
            mechanism_blocks=((0,), (1,), tuple()),
            future_universe=(0, 1),
            present_universe=(0, 1),
        )


def test_kpartition_accepts_k3_with_all_blocks_non_vacuous() -> None:
    """A genuine 3-way split (each part non-empty across either layer) is valid."""
    partition = KPartition(
        purview_blocks=((0,), (1,), tuple()),
        mechanism_blocks=((0,), (1,), (2,)),
        future_universe=(0, 1),
        present_universe=(0, 1, 2),
    )
    assert partition.k == 3
    # The future-empty block is non-vacuous because its mechanism part is non-empty.
    assert ((), (2,)) in partition.signature


def test_kpartition_rejects_single_non_vacuous_block() -> None:
    """Trivial partition (one block holds all) is rejected."""
    with pytest.raises(ValueError, match="non-vacuous"):
        KPartition(
            purview_blocks=(tuple(), (0, 1)),
            mechanism_blocks=(tuple(), (0, 1)),
            future_universe=(0, 1),
            present_universe=(0, 1),
        )


def test_kpartition_rejects_non_covering_blocks() -> None:
    with pytest.raises(ValueError, match="exactly cover"):
        KPartition(
            purview_blocks=((0,), (1,)),
            mechanism_blocks=((0,), ()),
            future_universe=(0, 1, 2),
            present_universe=(0,),
        )


def test_kpartition_canonicalizes_signature_deterministically() -> None:
    partition = KPartition.from_blocks(
        blocks=[
            (np.array([1], dtype=np.int8), np.array([0], dtype=np.int8)),
            (np.array([0], dtype=np.int8), np.array([1], dtype=np.int8)),
        ],
        future_universe=np.array([0, 1], dtype=np.int8),
        present_universe=np.array([0, 1], dtype=np.int8),
    )

    assert partition.signature == (((0,), (1,)), ((1,), (0,)))
