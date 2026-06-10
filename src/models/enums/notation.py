"""Binary index notations used when (re)ordering TPM states."""

from enum import Enum


class Notation(Enum):
    """Binary notations for dataset indexing and operations."""

    LIL_ENDIAN = "little-endian"
    BIG_ENDIAN = "big-endian"
