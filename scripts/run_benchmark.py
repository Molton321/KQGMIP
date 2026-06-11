"""Systematic benchmark: all strategies x all networks x all k values.

Writes the CSV consumed by the web UI and the figures (BENCHMARK_CSV) plus a
companion .xlsx with pivot summaries. Re-run it after changing any strategy to
keep the benchmark current (also available as uv run exec.py benchmark).

Usage:
    uv run scripts/run_benchmark.py                    # default grid (N10, N15)
    uv run scripts/run_benchmark.py --quick            # N10 only, k=2,3
    uv run scripts/run_benchmark.py --nets N20A N25A   # any sampled network
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.constants.base import BENCHMARK_CSV
from src.funcs.runner import load_tpm, parse_net_label, run_analysis
from src.models.base.application import application


def _strategy_specs(n: int, include_meta: bool) -> list[tuple[str, str, str]]:
    """Return a list of (label, key, method) for the strategies to run on a net of size n."""
    specs = [
        ("KGeoMIP", "KGeoMIP", "spectral"),
        ("KQNodes", "KQNodes", "spectral"),
        ("Clustering_spectral", "Clustering", "spectral"),
        ("Clustering_kmeans", "Clustering", "kmeans"),
    ]
    if include_meta:
        specs += [
            ("Genetic", "Genetic", "spectral"),
            ("Annealing", "Annealing", "spectral"),
            ("Tabu", "Tabu", "spectral"),
        ]
    if n <= 6:
        specs.append(("ExhaustiveK", "ExhaustiveK", "spectral"))
    return specs


def run_one(net: str, k: int, include_meta: bool = True) -> list[dict]:
    """Run every strategy for (net, k) and return result rows."""
    n, page, state = parse_net_label(net)
    application.set_sample_network_page(page)
    try:
        tpm = load_tpm(state, page)
    except FileNotFoundError:
        return [
            {
                "strategy": "ALL",
                "network": net,
                "n": n,
                "k": k,
                "loss": None,
                "time_s": None,
                "partition": None,
                "error": "TPM not found",
            }
        ]

    rows = []
    for label, key, method in _strategy_specs(n, include_meta):
        try:
            start = time.perf_counter()
            result = run_analysis(tpm, state, key, k, method=method)
            elapsed = time.perf_counter() - start
            rows.append(
                {
                    "strategy": label,
                    "network": net,
                    "n": n,
                    "k": k,
                    "loss": round(result.solution.loss, 6),
                    "time_s": round(elapsed, 4),
                    "partition": result.solution.partition,
                    "error": None,
                }
            )
        except Exception as e:
            rows.append(
                {
                    "strategy": label,
                    "network": net,
                    "n": n,
                    "k": k,
                    "loss": None,
                    "time_s": None,
                    "partition": None,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
    return rows


def main():
    """Parse CLI options, run the benchmark grid and write the CSV/XLSX."""
    parser = argparse.ArgumentParser(
        description="Benchmark all strategies x networks x k"
    )
    parser.add_argument(
        "--nets", nargs="*", default=None, help="Networks to test (default: N10A, N15A)"
    )
    parser.add_argument(
        "--ks", nargs="*", type=int, default=[2, 3, 4, 5], help="k values to test"
    )
    parser.add_argument("--max-n", type=int, default=25, help="Max network size")
    parser.add_argument(
        "--quick", action="store_true", help="Quick mode: N10 only, k=2,3"
    )
    parser.add_argument(
        "--no-meta", action="store_true", help="Skip metaheuristics (GA/SA/Tabu)"
    )
    parser.add_argument("--out", default=str(BENCHMARK_CSV), help="Output CSV path")
    args = parser.parse_args()

    application.disable_profiling()

    if args.quick:
        nets = ["N10A"]
        ks = [2, 3]
    elif args.nets:
        nets = args.nets
        ks = args.ks
    else:
        nets = ["N10A", "N15A"]
        ks = args.ks

    nets = [n for n in nets if int(n[1:-1]) <= args.max_n]

    print(f"Benchmark grid: {len(nets)} nets x {len(ks)} k values")
    print(f"Networks: {nets}")
    print(f"k values: {ks}")
    print()

    all_rows = []
    total = len(nets) * len(ks)
    done = 0
    for net in nets:
        for k in ks:
            done += 1
            print(f"[{done}/{total}] {net} k={k} ... ", end="", flush=True)
            rows = run_one(net, k, include_meta=not args.no_meta)
            all_rows.extend(rows)
            ok = sum(1 for r in rows if r["error"] is None)
            fail = sum(1 for r in rows if r["error"] is not None)
            print(f"{ok} ok, {fail} fail")

    df = pd.DataFrame(all_rows)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"\nCSV saved: {output}")

    xlsx_path = output.with_suffix(".xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Benchmark")
        pivot = df.pivot_table(
            index=["strategy", "network", "n"], columns="k", values="loss"
        )
        pivot.to_excel(writer, sheet_name="Loss Summary")
    print(f"Excel saved: {xlsx_path}")

    print("\n=== LOSS SUMMARY (lower is better) ===")
    pivot = df.pivot_table(index=["strategy", "network"], columns="k", values="loss")
    print(pivot.to_string())

    print("\n=== TIME SUMMARY (seconds) ===")
    pivot_t = df.pivot_table(
        index=["strategy", "network"], columns="k", values="time_s"
    )
    print(pivot_t.to_string())


if __name__ == "__main__":
    main()
