"""Visualization helpers for k-partitions (Phase 7 static, Phase 9-B interactive).

Re-exports the static matplotlib figures (``plot_kpartition``,
``plot_hypercube_partition``) and the interactive Plotly figures
(``plot_*_interactive``) so callers import them from one place.
"""

from src.viz.interactive import (
    plot_kpartition_interactive,
    plot_loss_vs_k_interactive,
    plot_scalability_interactive,
)
from src.viz.partition_plot import plot_hypercube_partition, plot_kpartition

__all__ = [
    "plot_kpartition",
    "plot_hypercube_partition",
    "plot_kpartition_interactive",
    "plot_loss_vs_k_interactive",
    "plot_scalability_interactive",
]
