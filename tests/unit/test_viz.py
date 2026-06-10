"""Smoke tests for the k-partition visualization (Phase 7)."""

from src.models.core.partition import KPartition
from src.viz import plot_hypercube_partition, plot_kpartition


def _partition():
    return KPartition.from_blocks(
        blocks=[((0,), (0,)), ((1,), (1, 2))],
        future_universe=(0, 1),
        present_universe=(0, 1, 2),
    )


def test_plot_kpartition_writes_png(tmp_path) -> None:
    out = tmp_path / "kpartition.png"
    result = plot_kpartition(_partition(), "test", str(out))
    assert result == str(out)
    assert out.exists() and out.stat().st_size > 0


def test_plot_hypercube_partition_writes_png(tmp_path) -> None:
    out = tmp_path / "hypercube.png"
    plot_hypercube_partition(_partition(), "test", str(out))
    assert out.exists() and out.stat().st_size > 0
