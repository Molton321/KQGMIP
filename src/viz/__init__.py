"""Visualization helpers for k-partitions (Phase 7 static, Phase 9-B interactive).

The static matplotlib views are always available. The interactive Plotly views
are imported lazily by name to avoid forcing the optional ``viz`` extra on
callers that only need the static figures.
"""

from typing import TYPE_CHECKING

from src.viz.partition_plot import plot_hypercube_partition, plot_kpartition

if TYPE_CHECKING:  # pragma: no cover - typing only
    from src.viz.interactive import (
        plot_kpartition_interactive,
        plot_loss_vs_k_interactive,
        plot_scalability_interactive,
    )

__all__ = [
    "plot_kpartition",
    "plot_hypercube_partition",
    "plot_kpartition_interactive",
    "plot_loss_vs_k_interactive",
    "plot_scalability_interactive",
]


def __getattr__(name: str):  # pragma: no cover - thin lazy re-export
    """Lazily expose the Plotly views (require the optional ``viz`` extra)."""
    if name in {
        "plot_kpartition_interactive",
        "plot_loss_vs_k_interactive",
        "plot_scalability_interactive",
    }:
        from src.viz import interactive

        return getattr(interactive, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
