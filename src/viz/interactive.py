"""Interactive Plotly views for k-partitions and benchmark grids (Fase 9-B).

These complement the static matplotlib figures in :mod:`src.viz.partition_plot`
with browser-interactive equivalents (hover, zoom, toggle traces). Every
function returns a :class:`plotly.graph_objects.Figure`, so the same code feeds
both the standalone HTML export (:mod:`scripts.make_interactive`) and the
Streamlit web UI (``app/streamlit_app.py``).

Plotly is imported lazily so importing this module never forces the optional
``viz`` extra unless an interactive figure is actually requested.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.funcs.labels import ABECEDARY, LOWER_ABECEDARY
from src.models.core.partition import KPartition

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

# Qualitative palette shared with the static views for visual consistency.
_PALETTE = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3",
]


def _block_color(block_index: int) -> str:
    """Return the palette colour for a block, wrapping past the palette end."""
    return _PALETTE[block_index % len(_PALETTE)]


def plot_kpartition_interactive(partition: KPartition, title: str) -> Any:
    """Return an interactive two-layer block diagram of a k-partition.

    Present (mechanism) atoms sit on the bottom row and future (purview) atoms
    on the top row; each atom is coloured by the block it belongs to and shows
    its block index on hover. Mirrors :func:`src.viz.plot_kpartition`.

    Args:
        partition: the validated k-partition to render.
        title: figure title.

    Returns:
        A :class:`plotly.graph_objects.Figure`.
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    for block_index, (purview, mechanism) in enumerate(partition.signature):
        color = _block_color(block_index)
        # Future (purview) atoms on the top row.
        if purview:
            fig.add_trace(go.Scatter(
                x=list(purview),
                y=[1.0] * len(purview),
                mode="markers+text",
                text=[ABECEDARY[i] for i in purview],
                textposition="middle center",
                textfont={"color": "white", "size": 12},
                marker={"size": 28, "color": color},
                name=f"bloque {block_index + 1}",
                legendgroup=f"b{block_index}",
                hovertemplate=(
                    f"bloque {block_index + 1}<br>futuro %{{text}} (t+1)<extra></extra>"
                ),
            ))
        # Present (mechanism) atoms on the bottom row.
        if mechanism:
            fig.add_trace(go.Scatter(
                x=list(mechanism),
                y=[0.0] * len(mechanism),
                mode="markers+text",
                text=[LOWER_ABECEDARY[i] for i in mechanism],
                textposition="middle center",
                textfont={"color": "white", "size": 12},
                marker={"size": 28, "color": color},
                name=f"bloque {block_index + 1}",
                legendgroup=f"b{block_index}",
                showlegend=not bool(purview),  # avoid duplicate legend entries
                hovertemplate=(
                    f"bloque {block_index + 1}<br>presente %{{text}} (t)<extra></extra>"
                ),
            ))

    fig.update_layout(
        title=title,
        xaxis={"title": "índice de nodo", "showgrid": True, "gridcolor": "#eee"},
        yaxis={
            "tickvals": [0.0, 1.0],
            "ticktext": ["presente (t)", "futuro (t+1)"],
            "range": [-0.6, 1.6],
        },
        template="plotly_white",
        height=380,
    )
    return fig


def plot_loss_vs_k_interactive(df: pd.DataFrame, net: str) -> Any:
    """Return an interactive δ_k-vs-k line chart for one network.

    Args:
        df: a benchmark grid with columns ``strategy``, ``network``, ``k``,
            ``loss``.
        net: the network label to filter on (e.g. ``"N10A"``).

    Returns:
        A :class:`plotly.graph_objects.Figure` with one line per strategy.
    """
    import plotly.graph_objects as go

    subset = df[(df["network"] == net) & df["loss"].notna()]
    fig = go.Figure()
    for strategy, group in subset.groupby("strategy"):
        group = group.sort_values(by="k")
        fig.add_trace(go.Scatter(
            x=group["k"], y=group["loss"], mode="lines+markers", name=str(strategy),
            hovertemplate="%{fullData.name}<br>k=%{x}<br>δ_k=%{y:.6f}<extra></extra>",
        ))
    fig.update_layout(
        title=f"Pérdida de información δ_k vs k — {net}",
        xaxis={"title": "k (bloques)", "dtick": 1},
        yaxis={"title": "δ_k"},
        template="plotly_white",
        height=460,
    )
    return fig


def plot_scalability_interactive(df: pd.DataFrame, k: int) -> Any:
    """Return an interactive runtime-vs-n chart (log y) at a fixed k.

    Args:
        df: a benchmark grid with columns ``strategy``, ``n``, ``k``, ``time_s``.
        k: the number of blocks to filter on.

    Returns:
        A :class:`plotly.graph_objects.Figure` with one line per strategy.
    """
    import plotly.graph_objects as go

    subset = df[(df["k"] == k) & df["time_s"].notna()]
    fig = go.Figure()
    for strategy, group in subset.groupby("strategy"):
        group = group.sort_values(by="n")
        fig.add_trace(go.Scatter(
            x=group["n"], y=group["time_s"], mode="lines+markers", name=str(strategy),
            hovertemplate="%{fullData.name}<br>n=%{x}<br>t=%{y:.4f}s<extra></extra>",
        ))
    fig.update_layout(
        title=f"Escalabilidad — tiempo vs n (k={k})",
        xaxis={"title": "n (nodos)"},
        yaxis={"title": "tiempo (s)", "type": "log"},
        template="plotly_white",
        height=460,
    )
    return fig
