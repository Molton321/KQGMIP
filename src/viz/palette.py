"""Shared block-color accessor for the static and interactive figures."""

from src.constants.base import BLOCK_PALETTE


def block_color(block_index: int) -> str:
    """Return the palette color for a block, cycling when blocks exceed it."""
    return BLOCK_PALETTE[block_index % len(BLOCK_PALETTE)]
