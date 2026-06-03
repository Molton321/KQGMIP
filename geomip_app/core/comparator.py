"""
comparator.py — Validaciones y análisis de resultados
"""
from __future__ import annotations
from typing import Any


def validar_resultados(resultados: dict[str, Any]) -> dict[str, dict]:
    """
    Ejecuta validaciones automáticas sobre los resultados.

    Returns:
        {'nombre_validacion': {'ok': bool, 'msg': str}, ...}
    """
    validaciones: dict[str, dict] = {}

    exitosos = {k: v for k, v in resultados.items() if "error" not in v and v.get("phi") is not None}

    if len(exitosos) < 1:
        return {"Sin resultados": {"ok": False, "msg": "Ninguna estrategia completó exitosamente"}}

    # Validación 1: consistencia de φ
    phis = {k: v["phi"] for k, v in exitosos.items()}
    if len(phis) >= 2:
        max_phi = max(phis.values())
        min_phi = min(phis.values())
        diff = max_phi - min_phi
        validaciones["Consistencia φ"] = {
            "ok": diff < 0.001,
            "msg": f"diferencia máxima entre estrategias: {diff:.6f} "
                   f"(min={min_phi:.6f}, max={max_phi:.6f})",
        }
    else:
        validaciones["Consistencia φ"] = {
            "ok": True,
            "msg": "Solo una estrategia ejecutada, no hay comparación posible",
        }

    # Validación 2: φ ≥ 0
    phi_negativo = {k: v for k, v in phis.items() if v < -1e-9}
    validaciones["φ no negativo"] = {
        "ok": len(phi_negativo) == 0,
        "msg": "todos los φ ≥ 0" if not phi_negativo else f"φ negativo en: {list(phi_negativo)}",
    }

    # Validación 3: tiempos razonables
    tiempos = {k: v.get("tiempo", 0) for k, v in exitosos.items() if v.get("tiempo") is not None}
    if tiempos:
        mas_lento = max(tiempos, key=tiempos.get)
        mas_rapido = min(tiempos, key=tiempos.get)
        speedup = tiempos[mas_lento] / max(tiempos[mas_rapido], 1e-9)
        validaciones["Speedup"] = {
            "ok": True,
            "msg": f"{mas_rapido} es {speedup:.1f}× más rápido que {mas_lento}",
        }

    # Validación 4: errores
    con_error = [k for k, v in resultados.items() if "error" in v]
    validaciones["Sin errores"] = {
        "ok": len(con_error) == 0,
        "msg": "todas las estrategias completaron sin error"
        if not con_error
        else f"errores en: {con_error}",
    }

    return validaciones


def tabla_speedup(resultados: dict[str, Any]) -> list[dict]:
    """Genera filas para tabla de speedup relativo."""
    exitosos = {k: v for k, v in resultados.items() if v.get("tiempo") is not None}
    if not exitosos:
        return []

    max_t = max(v["tiempo"] for v in exitosos.values()) or 1.0
    rows = []
    for nombre, v in exitosos.items():
        t = v["tiempo"]
        rows.append({
            "Estrategia": nombre,
            "Tiempo (s)": round(t, 4),
            "Speedup vs más lenta": round(max_t / max(t, 1e-9), 2),
            "φ": round(v["phi"], 6) if v.get("phi") is not None else "N/A",
        })
    rows.sort(key=lambda r: r["Tiempo (s)"])
    return rows
