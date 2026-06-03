"""
exporter.py — Exportación de resultados a Excel, CSV y JSON
"""
from __future__ import annotations
import io
import json
import datetime
import pandas as pd
from typing import Any


def _df_resultados(resultados: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for nombre, v in resultados.items():
        rows.append({
            "Estrategia": nombre,
            "φ (phi)": round(v["phi"], 6) if v.get("phi") is not None else "ERROR",
            "Tiempo (s)": round(v["tiempo"], 4) if v.get("tiempo") is not None else "N/A",
            "Evaluaciones": v.get("evaluaciones") or "N/A",
            "Partición": str(v.get("particion", ""))[:200],
            "Error": v.get("error", ""),
        })
    return pd.DataFrame(rows)


def exportar_excel(resultados: dict[str, Any], config: dict | None = None) -> bytes:
    """Exporta resultados a Excel en memoria, retorna bytes."""
    config = config or {}
    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Hoja 1: resultados
        df = _df_resultados(resultados)
        df.to_excel(writer, sheet_name="Resultados", index=False)

        # Hoja 2: metadatos
        ts = config.get("timestamp")
        if ts:
            fecha = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        else:
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        meta = pd.DataFrame([
            {"Campo": "Red", "Valor": config.get("tpm_nombre", "N/A")},
            {"Campo": "K", "Valor": config.get("k", "N/A")},
            {"Campo": "Estado inicial", "Valor": config.get("estado_inicial", "N/A")},
            {"Campo": "Condiciones", "Valor": config.get("condiciones", "N/A")},
            {"Campo": "Alcance", "Valor": config.get("alcance", "N/A")},
            {"Campo": "Mecanismo", "Valor": config.get("mecanismo", "N/A")},
            {"Campo": "Fecha", "Valor": fecha},
        ])
        meta.to_excel(writer, sheet_name="Config", index=False)

    return buf.getvalue()


def exportar_csv(resultados: dict[str, Any]) -> str:
    """Exporta resultados a CSV como string."""
    return _df_resultados(resultados).to_csv(index=False)


def exportar_json(resultados: dict[str, Any]) -> str:
    """Exporta resultados a JSON serializable."""
    safe = {}
    for nombre, v in resultados.items():
        safe[nombre] = {
            "phi": v.get("phi"),
            "particion": str(v.get("particion", "")),
            "tiempo": v.get("tiempo"),
            "evaluaciones": v.get("evaluaciones"),
            "error": v.get("error", ""),
        }
    return json.dumps(safe, indent=2, ensure_ascii=False)
