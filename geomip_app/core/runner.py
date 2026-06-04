"""
runner.py — Orquestación de estrategias de análisis MIP
"""
from __future__ import annotations
import sys
import time
import glob
import numpy as np
from pathlib import Path
from typing import Any

# ── Configurar sys.path para encontrar el proyecto ───────────────────────────
_REPO = Path(__file__).resolve().parents[2]
_METHOD2 = _REPO / "GeoMIP" / "src" / "Method2_Dynamic_Programming_Reformulation"
_VENV_SITE = _METHOD2 / ".venv"

# Añadir raíz del módulo src
_src_root = str(_METHOD2)
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

# Añadir site-packages del venv del proyecto para encontrar colorama, pyttsx3, etc.
for _sp in _VENV_SITE.glob("lib/python*/site-packages"):
    _sp_str = str(_sp)
    if _sp_str not in sys.path:
        sys.path.insert(1, _sp_str)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resultado_error(estrategia: str, msg: str) -> dict:
    return {
        "estrategia": estrategia,
        "error": str(msg),
        "phi": None,
        "particion": None,
        "tiempo": None,
    }


def _ejecutar_geometric(
    gestor, condicion: str, alcance: str, mecanismo: str, tpm: np.ndarray
) -> dict:
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


def _ejecutar_geometric_k(
    gestor, condicion: str, alcance: str, mecanismo: str, tpm: np.ndarray, k: int
) -> dict:
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


def _ejecutar_qnodes(
    gestor, condicion: str, alcance: str, mecanismo: str, tpm: np.ndarray
) -> dict:
    from src.controllers.strategies.q_nodes import QNodes
    sia = QNodes(gestor)
    t0 = time.perf_counter()
    # QNodes carga tpm internamente vía sia_preparar_subsistema(tpm=None)
    sol = sia.aplicar_estrategia(condicion, alcance, mecanismo)
    return {
        "phi": float(sol.perdida),
        "particion": str(sol.particion),
        "tiempo": time.perf_counter() - t0,
        "evaluaciones": None,
    }


def _ejecutar_phi(
    gestor, condicion: str, alcance: str, mecanismo: str
) -> dict:
    # Phi requiere pyphi → pyemd → pot (compilación C++).
    # Si pot no está disponible, lanza ImportError descriptivo.
    try:
        import pyphi  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "PyPhi no está disponible: requiere 'pot' compilado con g++. "
            f"Detalle: {e}"
        ) from e
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


# ── Punto de entrada público ─────────────────────────────────────────────────

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
    Ejecuta las estrategias seleccionadas y retorna resultados.

    Args:
        tpm: matriz TPM (2^n, n)
        estado_inicial_str: bits ej '1000000000'
        condicion_str / alcance_str / mecanismo_str: bits ej '1111111111'
        k: número de particiones para Geometric_K
        estrategias: {nombre: bool}

    Returns:
        {nombre: {'phi', 'particion', 'tiempo', 'evaluaciones'} | {'error': str}}
    """
    if estrategias is None:
        estrategias = {"Geometric": True}

    from src.controllers.manager import Manager
    gestor = Manager(estado_inicial=estado_inicial_str)

    resultados: dict[str, Any] = {}

    if estrategias.get("Geometric", False):
        try:
            resultados["Geometric"] = _ejecutar_geometric(
                gestor, condicion_str, alcance_str, mecanismo_str, tpm
            )
        except Exception as e:
            resultados["Geometric"] = _resultado_error("Geometric", e)

    if estrategias.get("Geometric_K", False) and k >= 2:
        label = f"Geometric K={k}"
        try:
            resultados[label] = _ejecutar_geometric_k(
                gestor, condicion_str, alcance_str, mecanismo_str, tpm, k
            )
        except Exception as e:
            resultados[label] = _resultado_error(label, e)

    if estrategias.get("QNodes", False):
        try:
            resultados["QNodes"] = _ejecutar_qnodes(
                gestor, condicion_str, alcance_str, mecanismo_str, tpm
            )
        except Exception as e:
            resultados["QNodes"] = _resultado_error("QNodes", e)

    if estrategias.get("Phi", False):
        try:
            resultados["Phi (PyPhi)"] = _ejecutar_phi(
                gestor, condicion_str, alcance_str, mecanismo_str
            )
        except Exception as e:
            resultados["Phi (PyPhi)"] = _resultado_error("Phi (PyPhi)", e)

    return resultados


def verificar_disponibilidad() -> dict[str, bool | str]:
    """
    Verifica qué estrategias pueden importarse.
    Útil para mostrar advertencias en la UI al arrancar.
    """
    estado: dict[str, bool | str] = {}

    for nombre, stmt in [
        ("Geometric", "from src.controllers.strategies.geometric import GeometricSIA"),
        ("QNodes",    "from src.controllers.strategies.q_nodes import QNodes"),
        ("Phi",       "import pyphi"),
    ]:
        try:
            exec(stmt)
            estado[nombre] = True
        except Exception as e:
            estado[nombre] = str(e)

    return estado
