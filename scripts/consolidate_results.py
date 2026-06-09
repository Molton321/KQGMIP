"""Consolidate the honest-hybrid benchmark grid into the FINAL deliverable.

The full grid is assembled from several runs of different feasibility so the
scalability ceiling is documented honestly rather than hidden:

- **Core grid** (``benchmark_core_meta.csv``): N10A/N15A, every strategy
  (KGeoMIP, KQNodes, Clustering ×2, GA/SA/Tabú) with a real δ_k.
- **n=20 core** (``benchmark_N20A_kgeomip.csv``): KGeoMIP only — the geometric
  core still computes δ_k at n=20 (~80 s/k); KQNodes' Queyranne O(n³·2ⁿ) and the
  exact search are impractical there.
- **n=25 proposal** (``benchmark_results_N25A_clustering.csv``): the clustering
  baseline *proposes* a partition at n=25, but δ_k is left blank because the
  2²⁵ reconstruction exceeds memory — this marks the documented ceiling.

    uv run scripts/consolidate_results.py

Writes ``data/results/benchmark_results_FINAL.csv`` and ``.xlsx``.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "results"

SOURCES = [
    "benchmark_core_meta.csv",
    "benchmark_N20A_kgeomip.csv",
    "benchmark_results_N25A_clustering.csv",
]
"""Source CSVs in the order they should stack into the final grid."""

COLUMNS = ["strategy", "network", "n", "k", "loss", "time_s", "partition", "error"]


def main() -> None:
    """Stack the source grids into the FINAL CSV/XLSX in a stable column order.

    Missing sources are skipped and absent columns (e.g. an explicit error
    column) are tolerated so partial grids still consolidate.
    """
    frames = []
    for name in SOURCES:
        path = RESULTS / name
        if not path.exists():
            print(f"WARN: missing source {name} (skipping)")
            continue
        frames.append(pd.read_csv(path))
    if not frames:
        print("No source CSVs found; run scripts/run_benchmark.py first.")
        sys.exit(1)

    df = pd.concat(frames, ignore_index=True)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS]
    df = df.sort_values(by=["n", "k", "strategy"], kind="stable").reset_index(drop=True)

    out_csv = RESULTS / "benchmark_results_FINAL.csv"
    df.to_csv(out_csv, index=False)
    print(f"CSV  -> {out_csv} ({len(df)} rows)")

    out_xlsx = RESULTS / "benchmark_results_FINAL.xlsx"
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Benchmark")
        pivot = df.pivot_table(index=["strategy", "network", "n"], columns="k", values="loss")
        pivot.to_excel(writer, sheet_name="Loss Summary")
    print(f"XLSX -> {out_xlsx}")

    print("\n=== δ_k by strategy x (net, k) ===")
    print(df.pivot_table(index=["strategy", "network"], columns="k", values="loss").to_string())


if __name__ == "__main__":
    main()
