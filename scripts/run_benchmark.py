"""Systematic benchmark: all strategies x all networks x all k values.

Generates a CSV + Excel with: strategy, network, n, k, loss, time_s, partition.
Designed to feed Fase 7 (experimentation) and docs/manuales/.

Usage:
    uv run scripts/run_benchmark.py                    # full grid (N10, N15)
    uv run scripts/run_benchmark.py --quick            # N10 only
    uv run scripts/run_benchmark.py --nets N6A N10A    # custom nets
    uv run scripts/run_benchmark.py --max-n 15         # cap network size
"""

import argparse
import contextlib
import io
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.controllers.manager import Manager
from src.models.base.application import application

StrategyFactory = Callable[[], Any]

# ---------------------------------------------------------------------------
# Strategy registry: all 7 strategies + legacy k=2 baselines
# ---------------------------------------------------------------------------

def _make_strategies(
    net: str, k: int, include_meta: bool = True
) -> tuple[list[tuple[str, StrategyFactory]], str]:
    """Return list of (label, strategy_factory) for the given net/k."""
    from src.controllers.strategies.clustering import ClusteringSIA
    from src.controllers.strategies.exhaustive_k import ExhaustiveK
    from src.controllers.strategies.kgeomip import KGeoMIP
    from src.controllers.strategies.kqnodes import KQNodes
    from src.controllers.strategies.metaheuristics import (
        AnnealingSIA,
        GeneticSIA,
        TabuSIA,
    )

    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n

    strategies: list[tuple[str, StrategyFactory]] = []

    # --- k-partition strategies (the core deliverables) ---
    strategies.append(("KGeoMIP", lambda: KGeoMIP(tpm, state, k=k)))
    strategies.append(("KQNodes", lambda: KQNodes(tpm, state, k=k)))
    strategies.append(("Clustering_spectral", lambda: ClusteringSIA(tpm, state, k=k, method="spectral")))
    strategies.append(("Clustering_kmeans", lambda: ClusteringSIA(tpm, state, k=k, method="kmeans")))

    # --- Metaheuristic comparative baselines (GA / SA / Tabu) ---
    if include_meta:
        strategies.append(("Genetic", lambda: GeneticSIA(tpm, state, k=k)))
        strategies.append(("Annealing", lambda: AnnealingSIA(tpm, state, k=k)))
        strategies.append(("Tabu", lambda: TabuSIA(tpm, state, k=k)))

    # --- ExhaustiveK: ground truth (only for small n) ---
    if n <= 6:
        strategies.append(("ExhaustiveK", lambda: ExhaustiveK(tpm, state, k=k)))

    return strategies, full


# ---------------------------------------------------------------------------
# Run a single benchmark
# ---------------------------------------------------------------------------

def run_one(net: str, k: int, include_meta: bool = True) -> list[dict]:
    """Run every strategy for (net, k) and return result rows."""
    n = int(net[1:-1])
    try:
        strategies, full = _make_strategies(net, k, include_meta=include_meta)
    except FileNotFoundError:
        return [{"strategy": "ALL", "network": net, "n": n, "k": k,
                 "loss": None, "time_s": None, "partition": None, "error": "TPM not found"}]

    rows = []
    for label, factory in strategies:
        try:
            start = time.perf_counter()
            with contextlib.redirect_stdout(io.StringIO()):
                analyzer = factory()
                solution = analyzer.apply_strategy(full, full, full)
            elapsed = time.perf_counter() - start
            rows.append({
                "strategy": label,
                "network": net,
                "n": n,
                "k": k,
                "loss": round(solution.loss, 6),
                "time_s": round(elapsed, 4),
                "partition": solution.partition,
                "error": None,
            })
        except Exception as e:
            rows.append({
                "strategy": label,
                "network": net,
                "n": n,
                "k": k,
                "loss": None,
                "time_s": None,
                "partition": None,
                "error": f"{type(e).__name__}: {e}",
            })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark all strategies x networks x k")
    parser.add_argument("--nets", nargs="*", default=None, help="Networks to test (default: N10A, N15A)")
    parser.add_argument("--ks", nargs="*", type=int, default=[2, 3, 4, 5], help="k values to test")
    parser.add_argument("--max-n", type=int, default=15, help="Max network size")
    parser.add_argument("--quick", action="store_true", help="Quick mode: N10 only, k=2,3")
    parser.add_argument("--no-meta", action="store_true", help="Skip metaheuristics (GA/SA/Tabu)")
    parser.add_argument("--output", default="data/results/benchmark_results.csv", help="Output CSV path")
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

    # Filter by max-n
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
            # Quick status
            ok = sum(1 for r in rows if r["error"] is None)
            fail = sum(1 for r in rows if r["error"] is not None)
            print(f"{ok} ok, {fail} fail")

    df = pd.DataFrame(all_rows)

    # Save CSV
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"\nCSV saved: {output}")

    # Save Excel
    xlsx_path = output.with_suffix(".xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Benchmark")
        # Summary sheet: pivot table loss by strategy x (net, k)
        pivot = df.pivot_table(index=["strategy", "network", "n"], columns="k", values="loss")
        pivot.to_excel(writer, sheet_name="Loss Summary")
    print(f"Excel saved: {xlsx_path}")

    # Print summary table
    print("\n=== LOSS SUMMARY (lower is better) ===")
    pivot = df.pivot_table(index=["strategy", "network"], columns="k", values="loss")
    print(pivot.to_string())

    print("\n=== TIME SUMMARY (seconds) ===")
    pivot_t = df.pivot_table(index=["strategy", "network"], columns="k", values="time_s")
    print(pivot_t.to_string())


if __name__ == "__main__":
    main()
