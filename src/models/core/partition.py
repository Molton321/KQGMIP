"""Validated k-partition data model for the IIT subsystem partitioning problem."""

import typing
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


def _normalize_unique(
    indices: tuple[int, ...] | list[int] | NDArray[np.int8], label: str
) -> tuple[int, ...]:
    """Normalize index collections into sorted tuples without duplicates."""
    normalized = tuple(int(i) for i in indices)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} contains duplicated indices: {normalized}")
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class KPartition:
    """Validated k-partition for present/future IIT indices.
    Enforces:
    - Matching number of purview and mechanism blocks.
    - All blocks are non-vacuous (doc §2.1).
    - Blocks are disjoint and exactly cover their respective universes.
    """

    purview_blocks: tuple[tuple[int, ...], ...]
    mechanism_blocks: tuple[tuple[int, ...], ...]
    future_universe: tuple[int, ...]
    present_universe: tuple[int, ...]

    def __post_init__(self) -> None:
        future_universe = _normalize_unique(self.future_universe, "future_universe")
        present_universe = _normalize_unique(self.present_universe, "present_universe")

        if len(self.purview_blocks) != len(self.mechanism_blocks):
            raise ValueError(
                "purview_blocks and mechanism_blocks must have the same length."
            )
        if len(self.purview_blocks) < 2:
            raise ValueError("k-partitions require at least 2 blocks.")

        normalized_pairs: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        non_vacuous_count = 0
        for idx, (purview, mechanism) in enumerate(
            zip(self.purview_blocks, self.mechanism_blocks, strict=True)
        ):
            purview_norm = _normalize_unique(purview, f"purview block {idx}")
            mechanism_norm = _normalize_unique(mechanism, f"mechanism block {idx}")

            if purview_norm or mechanism_norm:
                non_vacuous_count += 1

            normalized_pairs.append((purview_norm, mechanism_norm))

        total_blocks = len(self.purview_blocks)
        if non_vacuous_count < total_blocks:
            raise ValueError(
                f"strict k-partition requires all {total_blocks} blocks to be non-vacuous "
                f"(doc §2.1); found {non_vacuous_count} non-vacuous."
            )

        normalized_pairs.sort(key=lambda block: (block[0], block[1]))
        purview_blocks = tuple(purview for purview, _ in normalized_pairs)
        mechanism_blocks = tuple(mechanism for _, mechanism in normalized_pairs)

        self._validate_disjoint_and_cover(
            blocks=purview_blocks,
            universe=future_universe,
            domain_name="purview",
        )
        self._validate_disjoint_and_cover(
            blocks=mechanism_blocks,
            universe=present_universe,
            domain_name="mechanism",
        )

        object.__setattr__(self, "purview_blocks", purview_blocks)
        object.__setattr__(self, "mechanism_blocks", mechanism_blocks)
        object.__setattr__(self, "future_universe", future_universe)
        object.__setattr__(self, "present_universe", present_universe)

    @staticmethod
    def _validate_disjoint_and_cover(
        blocks: tuple[tuple[int, ...], ...],
        universe: tuple[int, ...],
        domain_name: str,
    ) -> None:
        """Ensure domain blocks are disjoint and exactly cover the universe."""
        seen: set[int] = set()
        for idx, block in enumerate(blocks):
            overlap = seen.intersection(block)
            if overlap:
                raise ValueError(
                    f"{domain_name} blocks are not disjoint. "
                    f"Overlap at block {idx}: {sorted(overlap)}"
                )
            seen.update(block)

        expected = set(universe)
        if seen != expected:
            missing = sorted(expected - seen)
            extra = sorted(seen - expected)
            raise ValueError(
                f"{domain_name} blocks must exactly cover the universe. "
                f"Missing: {missing}; Extra: {extra}"
            )

    @classmethod
    def from_blocks(
        cls,
        blocks: typing.Sequence[
            tuple[
                tuple[int, ...] | list[int] | NDArray[np.int8],
                tuple[int, ...] | list[int] | NDArray[np.int8],
            ]
        ],
        future_universe: tuple[int, ...] | list[int] | NDArray[np.int8],
        present_universe: tuple[int, ...] | list[int] | NDArray[np.int8],
    ) -> KPartition:
        """Build a validated (KPartition) from array-like block definitions."""
        purview_blocks = tuple(tuple(int(i) for i in purview) for purview, _ in blocks)
        mechanism_blocks = tuple(
            tuple(int(i) for i in mechanism) for _, mechanism in blocks
        )
        return cls(
            purview_blocks=purview_blocks,
            mechanism_blocks=mechanism_blocks,
            future_universe=tuple(int(i) for i in future_universe),
            present_universe=tuple(int(i) for i in present_universe),
        )

    @property
    def k(self) -> int:
        """Number of partition blocks."""
        return len(self.purview_blocks)

    @property
    def signature(self) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
        """Deterministic representation for hashing/memoization."""
        return tuple(zip(self.purview_blocks, self.mechanism_blocks, strict=True))
