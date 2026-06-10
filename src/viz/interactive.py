"""Interactive Plotly views for k-partitions and benchmark grids."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import plotly.graph_objects as go

from src.funcs.labels import ABECEDARY, LOWER_ABECEDARY
from src.models.core.partition import KPartition
from src.viz.palette import block_color

if TYPE_CHECKING:
    import pandas as pd


def plot_kpartition_interactive(partition: KPartition, title: str) -> Any:
    """Return an interactive two-layer block diagram of a k-partition.
    Each block is colored and labeled with its index. Hovering over a block shows
    the block index and its future/present nodes.
    """
    fig = go.Figure()
    for block_index, (purview, mechanism) in enumerate(partition.signature):
        color = block_color(block_index)
        if purview:
            fig.add_trace(
                go.Scatter(
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
                )
            )
        if mechanism:
            fig.add_trace(
                go.Scatter(
                    x=list(mechanism),
                    y=[0.0] * len(mechanism),
                    mode="markers+text",
                    text=[LOWER_ABECEDARY[i] for i in mechanism],
                    textposition="middle center",
                    textfont={"color": "white", "size": 12},
                    marker={"size": 28, "color": color},
                    name=f"bloque {block_index + 1}",
                    legendgroup=f"b{block_index}",
                    showlegend=not bool(purview),
                    hovertemplate=(
                        f"bloque {block_index + 1}<br>presente %{{text}} (t)<extra></extra>"
                    ),
                )
            )

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
    Each strategy is a separate line. Hovering over a point shows the strategy name,
    the k value, and the δ_k value.
    """
    subset = df[(df["network"] == net) & df["loss"].notna()]
    fig = go.Figure()
    for strategy, group in subset.groupby("strategy"):
        group = group.sort_values(by="k")
        fig.add_trace(
            go.Scatter(
                x=group["k"],
                y=group["loss"],
                mode="lines+markers",
                name=str(strategy),
                hovertemplate="%{fullData.name}<br>k=%{x}<br>δ_k=%{y:.6f}<extra></extra>",
            )
        )
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
    Each strategy is a separate line. Hovering over a point shows the strategy name,
    the n value, and the runtime in seconds.
    """
    subset = df[(df["k"] == k) & df["time_s"].notna()]
    fig = go.Figure()
    for strategy, group in subset.groupby("strategy"):
        group = group.sort_values(by="n")
        fig.add_trace(
            go.Scatter(
                x=group["n"],
                y=group["time_s"],
                mode="lines+markers",
                name=str(strategy),
                hovertemplate="%{fullData.name}<br>n=%{x}<br>t=%{y:.4f}s<extra></extra>",
            )
        )
    fig.update_layout(
        title=f"Escalabilidad — tiempo vs n (k={k})",
        xaxis={"title": "n (nodos)"},
        yaxis={"title": "tiempo (s)", "type": "log"},
        template="plotly_white",
        height=460,
    )
    return fig
