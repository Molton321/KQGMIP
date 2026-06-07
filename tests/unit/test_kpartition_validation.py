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
    with pytest.raises(ValueError, match="vacuous"):
        KPartition(
            purview_blocks=(tuple(), tuple()),
            mechanism_blocks=(tuple(), tuple()),
            future_universe=(0,),
            present_universe=(0,),
        )


def test_kpartition_allows_empty_blocks_when_two_non_vacuous_exist() -> None:
    """Empty blocks allowed when k > |universe|; at least 2 blocks must be non-vacuous."""
    partition = KPartition(
        purview_blocks=((0,), (1,), tuple()),
        mechanism_blocks=((0,), (1,), tuple()),
        future_universe=(0, 1),
        present_universe=(0, 1),
    )
    assert partition.k == 3
    assert partition.purview_blocks == ((), (0,), (1,))


def test_kpartition_rejects_single_non_vacuous_block() -> None:
    """Trivial partition (one block holds all) is rejected."""
    with pytest.raises(ValueError, match="at least 2 non-vacuous"):
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
