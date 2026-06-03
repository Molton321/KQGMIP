"""
visualizer.py — Gráficos interactivos con Plotly
"""
from __future__ import annotations
from typing import Any
import plotly.graph_objects as go


_COLORES = ["#0099cc", "#ff6b35", "#28a745", "#9b59b6", "#e74c3c"]


def _exitosos(resultados: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in resultados.items() if v.get("phi") is not None}


def graficar_phi(resultados: dict[str, Any]) -> go.Figure:
    """Gráfico de barras comparando φ entre estrategias."""
    datos = _exitosos(resultados)
    estrategias = list(datos.keys())
    phis = [datos[e]["phi"] for e in estrategias]

    fig = go.Figure(
        data=[
            go.Bar(
                x=estrategias,
                y=phis,
                marker_color=_COLORES[: len(estrategias)],
                text=[f"{p:.4f}" for p in phis],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="φ (phi) por estrategia",
        xaxis_title="Estrategia",
        yaxis_title="φ",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#e8e8e8"),
        margin=dict(t=50, b=40),
    )
    return fig


def graficar_tiempo(resultados: dict[str, Any]) -> go.Figure:
    """Gráfico de barras horizontal de tiempos de ejecución."""
    datos = {k: v for k, v in resultados.items() if v.get("tiempo") is not None}
    estrategias = list(datos.keys())
    tiempos = [datos[e]["tiempo"] for e in estrategias]

    fig = go.Figure(
        data=[
            go.Bar(
                x=tiempos,
                y=estrategias,
                orientation="h",
                marker_color=_COLORES[: len(estrategias)],
                text=[f"{t:.4f}s" for t in tiempos],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="Tiempo de ejecución por estrategia",
        xaxis_title="Tiempo (segundos)",
        yaxis_title="Estrategia",
        plot_bgcolor="white",
        xaxis=dict(gridcolor="#e8e8e8"),
        margin=dict(t=50, b=40),
    )
    return fig


def graficar_radar(resultados: dict[str, Any]) -> go.Figure:
    """Gráfico radar normalizando φ y speedup."""
    datos = _exitosos(resultados)
    if len(datos) < 2:
        return go.Figure().update_layout(title="Se necesitan ≥2 estrategias para radar")

    categorias = ["φ normalizado", "Velocidad (1/t normalizado)"]

    phis = [v["phi"] for v in datos.values()]
    tiempos = [v.get("tiempo", 1) or 1 for v in datos.values()]

    max_phi = max(phis) or 1
    max_t = max(tiempos) or 1

    fig = go.Figure()
    colores = _COLORES
    for idx, (nombre, v) in enumerate(datos.items()):
        phi_norm = v["phi"] / max_phi
        speed_norm = (1 / max(v.get("tiempo", max_t) or max_t, 1e-9)) / (1 / 1e-9 / max_t)
        # simplificado: velocidad relativa
        t = v.get("tiempo", max_t) or max_t
        speed_norm = (max_t / t) / len(datos)

        fig.add_trace(
            go.Scatterpolar(
                r=[phi_norm, speed_norm, phi_norm],
                theta=categorias + [categorias[0]],
                name=nombre,
                line_color=colores[idx % len(colores)],
            )
        )
    fig.update_layout(
        title="Radar: φ vs velocidad",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        margin=dict(t=60),
    )
    return fig


def graficar_distribucion(dist: list[float], titulo: str = "Distribución marginal") -> go.Figure:
    """Histograma de una distribución de probabilidad."""
    fig = go.Figure(
        data=[go.Bar(y=dist, marker_color="#0099cc")]
    )
    fig.update_layout(
        title=titulo,
        xaxis_title="Estado",
        yaxis_title="Probabilidad",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#e8e8e8", range=[0, 1]),
        margin=dict(t=50),
    )
    return fig
