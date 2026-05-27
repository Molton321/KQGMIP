from enum import Enum


class Notation(Enum):
    """Notaciones binarias para indexación de datasets y operaciones."""

    LIL_ENDIAN = "little-endian"
    BIG_ENDIAN = "big-endian"
    GRAY_CODE = "gray-code"
    SIGN_MAGNITUDE = "sign-magnitude"
    TWOS_COMPLEMENT = "two's-complement"
