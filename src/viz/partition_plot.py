"""Render k-partitions for the demo (Phase 7, official spec §4.4).

Two complementary views of a validated :class:`KPartition`:

- :func:`plot_kpartition` — a layered block diagram (present/mechanism row and
  future/purview row, each atom coloured by its block). Works for any ``n`` and
  any ``k``, so it is the general-purpose figure for the manuals/demo.
- :func:`plot_hypercube_partition` — for small systems (``n <= 4``), the
  n-dimensional hypercube of node indices drawn as a 2-D projection, with nodes
  coloured by their block. This is the literal "k regions of the hypercube"
  picture of the geometric interpretation (doc §2.3).

matplotlib is imported lazily (and forced to the headless ``Agg`` backend) so
importing this module never requires a display.
"""

from itertools import combinations

from src.funcs.labels import ABECEDARY, LOWER_ABECEDARY
from src.models.core.partition import KPartition

# A small qualitative palette; blocks beyond it wrap around.
_PALETTE = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3",
]


def _block_color(block_index: int) -> str:
    return _PALETTE[block_index % len(_PALETTE)]


def plot_kpartition(partition: KPartition, title: str, output_path: str) -> str:
    """Draw a k-partition as a two-layer block diagram and save a PNG.

    Args:
        partition: the validated k-partition to render.
        title: figure title.
        output_path: destination ``.png`` path.

    Returns:
        ``output_path`` (for convenience/chaining).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(max(6, partition.k * 2), 4))

    for block_index, (purview, mechanism) in enumerate(partition.signature):
        color = _block_color(block_index)
        # Future (purview) atoms on the top row, present (mechanism) on the bottom.
        for future_index in purview:
            ax.scatter(future_index, 1.0, s=420, color=color, zorder=3)
            ax.text(future_index, 1.0, ABECEDARY[future_index], ha="center", va="center",
                    color="white", fontweight="bold", zorder=4)
        for present_index in mechanism:
            ax.scatter(present_index, 0.0, s=420, color=color, zorder=3)
            ax.text(present_index, 0.0, LOWER_ABECEDARY[present_index], ha="center",
                    va="center", color="white", fontweight="bold", zorder=4)

    ax.set_yticks([0.0, 1.0])
    ax.set_yticklabels(["present (t)", "future (t+1)"])
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlabel("node index")
    ax.set_title(title)
    ax.grid(True, axis="x", alpha=0.2)
    legend = [Patch(color=_block_color(r), label=f"block {r + 1}") for r in range(partition.k)]
    ax.legend(handles=legend, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_hypercube_partition(partition: KPartition, title: str, output_path: str) -> str:
    """Draw the node hypercube (n<=4) with nodes coloured by their block.

    The node indices ``0..n-1`` are the hypercube dimensions; we lay the future
    atoms out as the vertices of an n-cube projection and connect Hamming-1
    neighbours, colouring each vertex by the block its future index belongs to.
    Falls back to :func:`plot_kpartition` for ``n > 4``.
    """
    universe = sorted(partition.future_universe)
    n = len(universe)
    if n > 4:
        return plot_kpartition(partition, title, output_path)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    future_block = {idx: r for r, (purview, _) in enumerate(partition.signature) for idx in purview}

    # 2-D projection: vertex v (a bit pattern over the n dims) placed by summing
    # unit vectors at angles spread over the circle (a standard n-cube layout).
    import numpy as np

    angles = np.linspace(0, np.pi, n, endpoint=False)
    axes_xy = np.array([[np.cos(a), np.sin(a)] for a in angles]) if n else np.zeros((0, 2))

    coords = {}
    for vertex in range(1 << n):
        bits = [(vertex >> i) & 1 for i in range(n)]
        coords[vertex] = axes_xy.T @ np.array(bits) if n else np.zeros(2)

    fig, ax = plt.subplots(figsize=(6, 6))
    # Hamming-1 edges.
    for a, b in combinations(range(1 << n), 2):
        if bin(a ^ b).count("1") == 1:
            xa, ya = coords[a]
            xb, yb = coords[b]
            ax.plot([xa, xb], [ya, yb], color="#cccccc", zorder=1)
    # Vertices coloured by the block of the future index they activate (single-bit
    # vertices map to a node/dimension; others are drawn neutral).
    for vertex, (x, y) in coords.items():
        if bin(vertex).count("1") == 1:
            dim = vertex.bit_length() - 1
            color = _block_color(future_block.get(universe[dim], 0))
        else:
            color = "#dddddd"
        ax.scatter(x, y, s=240, color=color, edgecolors="black", linewidths=0.5, zorder=2)

    ax.set_title(title)
    ax.set_aspect("equal")
    ax.axis("off")
    legend = [Patch(color=_block_color(r), label=f"block {r + 1}") for r in range(partition.k)]
    ax.legend(handles=legend, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output_path
