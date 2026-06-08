"""Export the interactive Plotly figures as standalone HTML (Fase 9-B).

Reads a benchmark grid (the CSV produced by ``run_benchmark.py``) and runs one
strategy on a small network, then writes self-contained ``.html`` files that
open in any browser with hover/zoom/legend-toggle:

- ``loss_vs_k_<net>.html``     — δ_k vs k per strategy, per network;
- ``scalability_k<k>.html``    — runtime vs n per strategy, per k;
- ``partition_<strategy>_<net>_k<k>.html`` — the best k-partition block diagram.

    uv run scripts/make_interactive.py
    uv run scripts/make_interactive.py --csv data/results/benchmark_results_FINAL.csv
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.controllers.manager import Manager
from src.controllers.strategies.kgeomip import KGeoMIP
from src.models.base.application import application
from src.viz import (
    plot_kpartition_interactive,
    plot_loss_vs_k_interactive,
    plot_scalability_interactive,
)


def _export(fig, out: Path) -> None:
    """Write a Plotly figure as a self-contained HTML file."""
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    print(f"  - {out.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export interactive Plotly figures")
    parser.add_argument("--csv", default="data/results/benchmark_results_FINAL.csv")
    parser.add_argument("--out", default="data/results/figures/interactive")
    parser.add_argument("--demo-net", default="N4A", help="network for the partition demo")
    parser.add_argument("--demo-k", type=int, default=3, help="k for the partition demo")
    args = parser.parse_args()

    application.disable_profiling()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path} (run scripts/run_benchmark.py first)")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Writing interactive figures to {out}:")

    # Grid figures (loss-vs-k per net, scalability per k).
    for net in df["network"].dropna().unique():
        if df[(df["network"] == net) & df["loss"].notna()].empty:
            continue
        _export(plot_loss_vs_k_interactive(df, str(net)), out / f"loss_vs_k_{net}.html")
    for k in sorted(df["k"].dropna().unique()):
        _export(plot_scalability_interactive(df, int(k)), out / f"scalability_k{int(k)}.html")

    # Partition demo figure (run KGeoMIP live on a small network).
    net = args.demo_net
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        analyzer = KGeoMIP(tpm, state, k=args.demo_k)
        solution = analyzer.apply_strategy(full, full, full)
    partition = analyzer.best_partition
    if partition is None:
        print("  (no partition produced; skipping partition demo)")
        return
    title = f"KGeoMIP — {net}, k={args.demo_k} (δ_k={solution.loss:.4f})"
    _export(
        plot_kpartition_interactive(partition, title),
        out / f"partition_KGeoMIP_{net}_k{args.demo_k}.html",
    )


if __name__ == "__main__":
    main()
