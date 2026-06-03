"""
runner.py — Orquestación de estrategias de análisis MIP
"""
from __future__ import annotations
import sys
import time
import numpy as np
from pathlib import Path
from typing import Any

# Añadir rutas del repo al path
_REPO = Path(__file__).resolve().parents[2]
_GEOMIP_SRC = _REPO / "GeoMIP" / "src" / "Method2_Dynamic_Programming_Reformulation"

for _p in [str(_GEOMIP_SRC), str(_REPO)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _resultado_error(estrategia: str, msg: str) -> dict:
    return {"estrategia": estrategia, "error": str(msg), "phi": None, "particion": None, "tiempo": None}


def _ejecutar_geometric(gestor, condicion: str, alcance: str, mecanismo: str, tpm: np.ndarray) -> dict:
    from src.controllers.strategies.geometric import GeometricSIA
    sia = GeometricSIA(gestor)
    t0 = time.perf_counter()
    sol = sia.aplicar_estrategia(condicion, alcance, mecanismo, tpm)
    return {
        "phi": float(sol.perdida),
        "particion": str(sol.particion),
        "tiempo": time.perf_counter() - t0,
        "evaluaciones": None,
    }


def _ejecutar_geometric_k(gestor, condicion: str, alcance: str, mecanismo: str, tpm: np.ndarray, k: int) -> dict:
    from src.controllers.strategies.geometric_k import GeometricSIA_K
    sia = GeometricSIA_K(gestor)
    t0 = time.perf_counter()
    res = sia.aplicar_estrategia_k(condicion, alcance, mecanismo, tpm, k=k)
    return {
        "phi": float(res["phi"]),
        "particion": str(res["particion"]),
        "tiempo": time.perf_counter() - t0,
        "evaluaciones": res.get("evaluaciones"),
    }


def _ejecutar_qnodes(gestor, condicion: str, alcance: str, mecanismo: str, tpm: np.ndarray) -> dict:
    from src.controllers.strategies.q_nodes import QNodes
    sia = QNodes(gestor)
    t0 = time.perf_counter()
    sol = sia.aplicar_estrategia(condicion, alcance, mecanismo, tpm)
    return {
        "phi": float(sol.perdida),
        "particion": str(sol.particion),
        "tiempo": time.perf_counter() - t0,
        "evaluaciones": None,
    }


def _ejecutar_phi(gestor, condicion: str, alcance: str, mecanismo: str) -> dict:
    from src.controllers.strategies.phi import Phi
    sia = Phi(gestor)
    t0 = time.perf_counter()
    sol = sia.aplicar_estrategia(condicion, alcance, mecanismo)
    return {
        "phi": float(sol.perdida),
        "particion": str(sol.particion),
        "tiempo": time.perf_counter() - t0,
        "evaluaciones": None,
    }


def ejecutar_estrategias(
    tpm: np.ndarray,
    estado_inicial_str: str,
    condicion_str: str,
    alcance_str: str,
    mecanismo_str: str,
    k: int = 2,
    estrategias: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta las estrategias seleccionadas sobre la TPM configurada.

    Args:
        tpm: matriz de probabilidad de transición (ndarray cuadrado)
        estado_inicial_str: string de bits, ej '1000000000'
        condicion_str: string de bits para condiciones de fondo
        alcance_str: string de bits para alcance (t+1)
        mecanismo_str: string de bits para mecanismo (t)
        k: número de particiones para Geometric K
        estrategias: dict con flags True/False por estrategia

    Returns:
        dict de resultados por estrategia
    """
    if estrategias is None:
        estrategias = {"Geometric": True, "QNodes": False, "Phi": False}

    # Importar Manager
    from src.controllers.manager import Manager
    gestor = Manager(estado_inicial=estado_inicial_str)

    resultados: dict[str, Any] = {}

    if estrategias.get("Geometric", False):
        try:
            resultados["Geometric"] = _ejecutar_geometric(gestor, condicion_str, alcance_str, mecanismo_str, tpm)
        except Exception as e:
            resultados["Geometric"] = _resultado_error("Geometric", e)

    if estrategias.get("Geometric_K", False) and k >= 2:
        try:
            resultados[f"Geometric K={k}"] = _ejecutar_geometric_k(gestor, condicion_str, alcance_str, mecanismo_str, tpm, k)
        except Exception as e:
            resultados[f"Geometric K={k}"] = _resultado_error(f"Geometric K={k}", e)

    if estrategias.get("QNodes", False):
        try:
            resultados["QNodes"] = _ejecutar_qnodes(gestor, condicion_str, alcance_str, mecanismo_str, tpm)
        except Exception as e:
            resultados["QNodes"] = _resultado_error("QNodes", e)

    if estrategias.get("Phi", False):
        try:
            resultados["Phi (PyPhi)"] = _ejecutar_phi(gestor, condicion_str, alcance_str, mecanismo_str)
        except Exception as e:
            resultados["Phi (PyPhi)"] = _resultado_error("Phi (PyPhi)", e)

    return resultados
