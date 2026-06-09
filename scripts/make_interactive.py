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
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# isort: split
from src.funcs.runner import load_tpm, parse_net_label, run_analysis
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

    for net in df["network"].dropna().unique():
        if df[(df["network"] == net) & df["loss"].notna()].empty:
            continue
        _export(plot_loss_vs_k_interactive(df, str(net)), out / f"loss_vs_k_{net}.html")
    for k in sorted(df["k"].dropna().unique()):
        _export(
            plot_scalability_interactive(df, int(k)),
            out / f"scalability_k{int(k)}.html",
        )

    net = args.demo_net
    _, page, state = parse_net_label(net)
    tpm = load_tpm(state, page)
    result = run_analysis(tpm, state, "KGeoMIP", args.demo_k)
    if result.partition is None:
        print("  (no partition produced; skipping partition demo)")
        return
    title = f"KGeoMIP — {net}, k={args.demo_k} (δ_k={result.solution.loss:.4f})"
    _export(
        plot_kpartition_interactive(result.partition, title),
        out / f"partition_KGeoMIP_{net}_k{args.demo_k}.html",
    )


if __name__ == "__main__":
    main()
