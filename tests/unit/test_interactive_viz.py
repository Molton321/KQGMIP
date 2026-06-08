"""Tests for the interactive Plotly views (:mod:`src.viz.interactive`).

Plotly is an optional extra, so the whole module is skipped when it is missing.
The checks confirm each helper returns a Plotly figure with the expected traces;
rendering itself is Plotly's responsibility, not ours.
"""

import pandas as pd
import pytest

pytest.importorskip("plotly")  # skip the module if the optional extra is absent

from src.funcs.runner import load_tpm, run_analysis  # noqa: E402
from src.models.base.application import application  # noqa: E402
from src.viz import (  # noqa: E402
    plot_kpartition_interactive,
    plot_loss_vs_k_interactive,
    plot_scalability_interactive,
)


def _benchmark_frame() -> pd.DataFrame:
    """A tiny synthetic benchmark grid for the grid-figure tests."""
    return pd.DataFrame(
        {
            "strategy": ["KGeoMIP", "KGeoMIP", "KQNodes", "KQNodes"],
            "network": ["N10A", "N10A", "N10A", "N10A"],
            "n": [10, 10, 10, 10],
            "k": [2, 3, 2, 3],
            "loss": [0.47, 0.94, 0.47, 0.94],
            "time_s": [0.05, 0.05, 0.18, 0.19],
        }
    )


def test_kpartition_interactive_returns_figure() -> None:
    """The partition diagram is a Plotly figure with at least one trace."""
    import plotly.graph_objects as go

    application.set_sample_network_page("A")
    tpm = load_tpm("1111", "A")
    result = run_analysis(tpm, "1111", "KGeoMIP", k=3)
    assert result.partition is not None
    fig = plot_kpartition_interactive(result.partition, "test")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


def test_loss_vs_k_interactive_has_trace_per_strategy() -> None:
    """One line is drawn per strategy present in the grid."""
    import plotly.graph_objects as go

    fig = plot_loss_vs_k_interactive(_benchmark_frame(), "N10A")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # KGeoMIP + KQNodes


def test_scalability_interactive_uses_log_axis() -> None:
    """The runtime figure uses a logarithmic y axis."""
    fig = plot_scalability_interactive(_benchmark_frame(), k=2)
    assert fig.layout.yaxis.type == "log"
