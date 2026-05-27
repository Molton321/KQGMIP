import numpy as np
from numpy.typing import NDArray

from src.constants.base import ABC_START, EMPTY_STR, STR_ONE, VOID_STR
from src.base.application import aplicacion
from src.models.enums.notation import Notation


def get_labels(n: int) -> tuple[str, ...]:
    """Genera etiquetas alfanuméricas estilo Excel (A, B, ..., Z, AA, AB, ...)."""
    def get_excel_column(n: int) -> str:
        if n <= 0:
            return ""
        return get_excel_column((n - 1) // 26) + chr((n - 1) % 26 + ord(ABC_START))

    return tuple(get_excel_column(i) for i in range(1, n + 1))


ABECEDARY: tuple[str, ...] = get_labels(40)
LOWER_ABECEDARY: list[str] = [letter.lower() for letter in ABECEDARY]


def literales(remaining_vars: NDArray[np.int8], lowercase: bool = False) -> str:
    """Convierte índices de variables a sus etiquetas literales (A, B, C...)."""
    return (
        EMPTY_STR.join(
            ABECEDARY[i].lower() if lowercase else ABECEDARY[i]
            for i in remaining_vars
        )
        if remaining_vars.size
        else VOID_STR
    )


def dec2bin(decimal: int, width: int) -> str:
    return format(decimal, f"0{width}b")


def estados_binarios(n: int) -> list[str]:
    """Genera todos los estados binarios no nulos para n nodos."""
    return [dec2bin(i, n) for i in range(1 << n)][1:]


def lil_endian(n: int) -> np.ndarray:
    """Genera la permutación de índices en notación little-endian."""
    if n <= 0:
        return np.array([0], dtype=np.uint32)

    size = 1 << n
    result = np.zeros(size, dtype=np.uint32)

    block_bits = max(12, min(16, 28 - int(np.log2(n))))
    block_size = 1 << block_bits
    shifts = np.array([n - i - 1 for i in range(n)], dtype=np.uint32)
    block_result = np.zeros(block_size, dtype=np.uint32)
    bit_group_size = 6 if n > 24 else 4

    for start in range(0, size, block_size):
        end = min(start + block_size, size)
        current_size = end - start
        block_result[:current_size] = 0
        block_indices = np.arange(start, end, dtype=np.uint32)

        for base_bit in range(0, n, bit_group_size):
            bits_remaining = min(bit_group_size, n - base_bit)
            if bits_remaining <= 0:
                break
            group_mask = np.uint32((1 << bits_remaining) - 1)
            group_values = (block_indices >> base_bit) & group_mask
            for j in range(bits_remaining):
                shift = shifts[base_bit + j]
                bit_value = (group_values >> j) & np.uint32(1)
                block_result[:current_size] |= bit_value << shift

        result[start:end] = block_result[:current_size]

    return result


def big_endian(n: int) -> np.ndarray:
    return np.array(range(n), dtype=np.uint32)


def reindexar(n: int) -> np.ndarray:
    """Selecciona la permutación de índices según la notación configurada."""
    notacion = aplicacion.notacion_indexado
    if isinstance(notacion, Notation):
        notacion = notacion.value

    notaciones = {
        Notation.BIG_ENDIAN.value: big_endian(n),
        Notation.LIL_ENDIAN.value: lil_endian(n),
    }
    if notacion not in notaciones:
        raise ValueError(
            f"Notación no soportada: '{notacion}'. "
            f"Opciones: {', '.join(sorted(notaciones))}"
        )
    return notaciones[notacion]


def seleccionar_estado(subestado: tuple) -> tuple:
    """Ajusta el orden de acceso al n-cubo según la notación configurada."""
    notacion = aplicacion.notacion_indexado
    if isinstance(notacion, Notation):
        notacion = notacion.value

    notaciones = {
        Notation.BIG_ENDIAN.value: subestado,
        Notation.LIL_ENDIAN.value: subestado[::-1],
    }
    if notacion not in notaciones:
        raise ValueError(
            f"Notación no soportada: '{notacion}'. "
            f"Opciones: {', '.join(sorted(notaciones))}"
        )
    return notaciones[notacion]
