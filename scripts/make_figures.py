"""Generate the Phase 7 figures from a benchmark CSV.

Reads the grid produced by ``run_benchmark.py`` and writes reproducible
matplotlib figures (no display backend required):

- scalability: runtime vs n (log scale) per strategy, for a fixed k;
- loss vs k per strategy, for a fixed network;
- strategy comparison: loss by strategy across the grid.

    uv run scripts/make_figures.py
    uv run scripts/make_figures.py --csv data/results/benchmark_results.csv
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _ok(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with a numeric loss/time (drop errors)."""
    return df[df["loss"].notna() & df["time_s"].notna()].copy()


def fig_scalability(df: pd.DataFrame, out: Path, k: int) -> None:
    """Runtime vs n (log y) per strategy, at a fixed k."""
    subset = _ok(df[df["k"] == k])
    if subset.empty:
        return
    plt.figure(figsize=(7, 4.5))
    for strategy, group in subset.groupby("strategy"):
        group = group.sort_values("n")
        plt.plot(group["n"], group["time_s"], marker="o", label=strategy)
    plt.yscale("log")
    plt.xlabel("n (nodes)")
    plt.ylabel("time (s, log)")
    plt.title(f"Scalability — runtime vs n (k={k})")
    plt.legend(fontsize=8)
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / f"scalability_k{k}.png", dpi=120)
    plt.close()


def fig_loss_vs_k(df: pd.DataFrame, out: Path, net: str) -> None:
    """Loss vs k per strategy, for one network."""
    subset = _ok(df[df["network"] == net])
    if subset.empty:
        return
    plt.figure(figsize=(7, 4.5))
    for strategy, group in subset.groupby("strategy"):
        group = group.sort_values("k")
        plt.plot(group["k"], group["loss"], marker="s", label=strategy)
    plt.xlabel("k (blocks)")
    plt.ylabel("δ_k loss")
    plt.title(f"Information loss vs k — {net}")
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out / f"loss_vs_k_{net}.png", dpi=120)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 7 figures")
    parser.add_argument("--csv", default="data/results/benchmark_results.csv")
    parser.add_argument("--out", default="data/results/figures")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path} (run scripts/run_benchmark.py first)")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for k in sorted(df["k"].dropna().unique()):
        fig_scalability(df, out, int(k))
    for net in df["network"].dropna().unique():
        fig_loss_vs_k(df, out, str(net))

    figures = sorted(p.name for p in out.glob("*.png"))
    print(f"Wrote {len(figures)} figures to {out}:")
    for name in figures:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
