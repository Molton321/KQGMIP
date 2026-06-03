"""
loader.py — Carga de datos de TPM
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from functools import lru_cache

# Ruta base de la app
APP_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = APP_DIR.parent
SAMPLES_DIR = REPO_DIR / "GeoMIP" / "data" / "samples"

# Redes disponibles — se descubren dinámicamente
def _descubrir_redes() -> dict[str, Path]:
    redes = {}
    if SAMPLES_DIR.exists():
        for csv in sorted(SAMPLES_DIR.glob("N*.csv")):
            redes[csv.stem] = csv
    return redes

REDES_PREDEFINIDAS: dict[str, Path] = _descubrir_redes()


def cargar_tpm(ruta_o_archivo) -> tuple[np.ndarray, int]:
    """
    Carga una TPM desde CSV, Excel o file-uploader de Streamlit.

    Returns:
        (tpm, n_nodos)
    """
    if isinstance(ruta_o_archivo, (str, Path)):
        ruta = Path(ruta_o_archivo)
        if ruta.suffix == ".csv":
            df = pd.read_csv(ruta, header=None)
        else:
            df = pd.read_excel(ruta, header=None)
    else:
        # Streamlit UploadedFile
        nombre = ruta_o_archivo.name
        if nombre.endswith(".csv"):
            df = pd.read_csv(ruta_o_archivo, header=None)
        else:
            df = pd.read_excel(ruta_o_archivo, header=None)

    tpm = df.values.astype(float)
    rows, cols = tpm.shape

    # Formato estándar: (2^n, n) — estados × nodos
    import math
    if rows > cols and math.log2(rows) == round(math.log2(rows), 6):
        n_nodos = cols  # columnas = nodos
    elif rows == cols:
        n_nodos = rows  # cuadrada (formato alternativo)
    else:
        raise ValueError(
            f"Formato TPM no reconocido: {tpm.shape}. "
            "Esperado (2^n, n) o (n, n)."
        )

    return tpm, n_nodos


def bits_a_string(nodos_activos: list[str], todas_letras: list[str]) -> str:
    """
    Convierte lista de letras activas a string de bits.
    ej: nodos_activos=['A','C'], todas=['A','B','C','D'] → '1010'
    """
    return "".join("1" if l in nodos_activos else "0" for l in todas_letras)


def estado_a_string(estado_bits: list[int]) -> str:
    """Convierte lista de ints [1,0,0,...] a string '100...'"""
    return "".join(str(b) for b in estado_bits)


@lru_cache(maxsize=None)
def stirling2(n: int, k: int) -> int:
    """Número de Stirling de segunda especie S(n, k)."""
    if n == 0 and k == 0:
        return 1
    if n == 0 or k == 0:
        return 0
    return k * stirling2(n - 1, k) + stirling2(n - 1, k - 1)
