"""
main_k.py
Punto de entrada para pruebas con K-particiones.
Ejecutar con: python -m src.main_k  (desde Method2_Dynamic_Programming_Reformulation/)
"""
from __future__ import annotations
import numpy as np
from pathlib import Path
import re
import os

from src.controllers.manager import Manager
from src.controllers.strategies.geometric_k import GeometricSIA_K
from src.funcs.k_partitions import stirling2


METHOD2_ROOT = Path(__file__).resolve().parents[1]
GEOMIP_ROOT = Path(__file__).resolve().parents[3]


def _resolver_tpm_path(n: int) -> Path:
    sample_name = f"N{n}A.csv"
    candidates = (
        METHOD2_ROOT / "src" / ".samples" / sample_name,
        METHOD2_ROOT / ".samples" / sample_name,
        GEOMIP_ROOT / "data" / "samples" / sample_name,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No se encontró '{sample_name}'. Busqué en: {', '.join(str(c) for c in candidates)}"
    )


def ejecutar_prueba_k(
    estado_inicial: str,
    condiciones: str,
    alcance: str,
    mecanismo: str,
    k: int = 3,
    verbose: bool = True,
) -> dict:
    """
    Ejecuta una prueba de K-partición y retorna resultados.

    Args:
        estado_inicial: string de bits, ej: "1000000000"
        condiciones: string de bits del mismo largo
        alcance: string de bits del mismo largo
        mecanismo: string de bits del mismo largo
        k: número de particiones
        verbose: si True imprime resultado formateado
    """
    n = len(estado_inicial)
    tpm_path = _resolver_tpm_path(n)
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    n_alc = alcance.count("1")
    n_mec = mecanismo.count("1")
    total_particiones = stirling2(n_alc, k) * stirling2(n_mec, k)

    if verbose:
        print(f"\n→ K={k}, N={n}, particiones a evaluar: {total_particiones:,}")

    gestor = Manager(estado_inicial=estado_inicial)
    estrategia = GeometricSIA_K(gestor)
    resultado = estrategia.aplicar_estrategia_k(
        condicion=condiciones,
        alcance=alcance,
        mecanismo=mecanismo,
        tpm=tpm,
        k=k,
    )

    if verbose:
        _imprimir_resultado(resultado, estado_inicial)

    return resultado


def comparar_k_particiones(
    estado_inicial: str,
    condiciones: str,
    alcance: str,
    mecanismo: str,
    k_max: int = 4,
) -> None:
    """
    Ejecuta K=2, 3, ..., k_max y compara φ y tiempos.
    Verifica que φ(K) >= φ(K+1) siempre.
    """
    print(f"\n{'K':>4} | {'φ (phi)':>12} | {'Tiempo(s)':>10} | {'Evaluaciones':>14} | Check")
    print("-" * 65)

    phi_anterior = None
    for k in range(2, k_max + 1):
        try:
            res = ejecutar_prueba_k(
                estado_inicial, condiciones, alcance, mecanismo,
                k=k, verbose=False,
            )
            phi = res["phi"]
            t   = res["tiempo"]
            ev  = res.get("evaluaciones", -1)

            check = ""
            if phi_anterior is not None:
                if phi > phi_anterior + 1e-6:
                    check = "BUG: phi aumentó"
                elif phi < phi_anterior - 1e-6:
                    check = "mejoró"
                else:
                    check = "igual"

            print(f"{k:4} | {phi:12.6f} | {t:10.4f} | {ev:>14,} | {check}")
            phi_anterior = phi

        except Exception as e:
            print(f"{k:4} | {'ERROR':>12} | {'—':>10} | {'—':>14} | {str(e)[:30]}")
            break

    print("-" * 65)


def _imprimir_resultado(resultado: dict, estado_inicial: str) -> None:
    k         = resultado.get("k", "?")
    phi       = resultado["phi"]
    t         = resultado["tiempo"]
    ev        = resultado.get("evaluaciones", "N/A")
    particion = resultado.get("particion")

    print(f"\n{'='*60}")
    print(f"  K-Partición Mínima  (K={k})")
    print(f"{'='*60}")
    print(f"  φ (phi)      : {phi:.6f}")
    print(f"  Tiempo       : {t:.4f}s")
    if isinstance(ev, int):
        print(f"  Evaluaciones : {ev:,}")
    else:
        print(f"  Evaluaciones : {ev}")

    if particion is not None and k != 2:
        letras = "ABCDEFGHIJKLMNOPQRST"
        ones = [i for i, b in enumerate(estado_inicial) if True]  # all positions
        print(f"\n  Partición óptima:")
        for i, (alc_i, mec_i) in enumerate(particion):
            alc_str = "".join(letras[j] for j in alc_i) if len(alc_i) else "∅"
            mec_str = "".join(letras[j] for j in mec_i) if len(mec_i) else "∅"
            print(f"    Grupo {i+1}: alcance=[{alc_str}] × mecanismo=[{mec_str}]")
    print(f"{'='*60}\n")


# ────────────────────────────────────────────────────────────────────
# Configuración de prueba — ajustar antes de ejecutar
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ESTADO_INICIAL = "1000000000"
    CONDICIONES    = "1111111111"
    ALCANCE        = "0101010101"
    MECANISMO      = "1111111111"

    # Prueba individual K=3
    ejecutar_prueba_k(
        estado_inicial=ESTADO_INICIAL,
        condiciones=CONDICIONES,
        alcance=ALCANCE,
        mecanismo=MECANISMO,
        k=3,
    )

    # Comparación K=2,3,4
    comparar_k_particiones(
        estado_inicial=ESTADO_INICIAL,
        condiciones=CONDICIONES,
        alcance=ALCANCE,
        mecanismo=MECANISMO,
        k_max=4,
    )
