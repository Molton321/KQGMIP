"""Correctness validation across strategies (Phase 7).

For each small network (where the exact ground truth is feasible) this runs every
k-strategy and checks, using the strategy's best_partition KPartition object
(never the formatted string):

1. the reported loss equals delta_k recomputed from that partition,
2. the loss never beats the exact ExhaustiveK optimum (exact is a lower bound),
3. it reports the exact-hit rate, relative Φ error and Jaccard distance to exact.

    uv run scripts/validate_correctness.py
    uv run scripts/validate_correctness.py --nets N3A N4A --ks 2 3
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# isort: split
from src.funcs.emd import delta_k
from src.funcs.metrics import is_exact_hit, jaccard_partition_distance, relative_phi_error
from src.funcs.runner import build_strategy, load_tpm, parse_net_label
from src.models.base.application import application

STRATEGIES = ["KGeoMIP", "KQNodes", "Clustering"]
"""Strategies validated against the exact optimum (built via the single registry)."""


def _run(name: str, tpm, state, k):
    """Run a strategy and return (solution, best_partition, subsystem, baseline)."""
    full = "1" * len(state)
    analyzer = build_strategy(name, tpm, state, k, "spectral")
    with contextlib.redirect_stdout(io.StringIO()):
        solution = analyzer.apply_strategy(full, full, full)
    return (
        solution,
        analyzer.best_partition,
        analyzer.sia_subsystem,
        analyzer.sia_marginal_dists,
    )


def validate_net(net: str, ks: list[int]) -> tuple[int, int]:
    """Validate every strategy/k for one network. Returns (passed, total)."""
    n, page, state = parse_net_label(net)
    application.set_sample_network_page(page)
    tpm = load_tpm(state, page)
    print(f"\n=== {net} (n={n}) ===")

    passed = total = 0
    for k in ks:
        if k > n:
            continue
        exact_sol, exact_part, _, _ = _run("ExhaustiveK", tpm, state, k)

        for label in STRATEGIES:
            total += 1
            try:
                sol, part, subsystem, baseline = _run(label, tpm, state, k)
                recomputed, _ = delta_k(subsystem, part, baseline_distribution=baseline)
                consistent = abs(float(recomputed) - sol.loss) < 1e-6
                lower_bounded = sol.loss >= exact_sol.loss - 1e-9
                hit = is_exact_hit(sol.loss, exact_sol.loss)
                phi_err = relative_phi_error(sol.loss, exact_sol.loss)
                jacc = jaccard_partition_distance(part, exact_part)

                ok = consistent and lower_bounded
                passed += ok
                flag = "OK " if ok else "BAD"
                hit_flag = "exact" if hit else f"+{phi_err:.1%}"
                print(
                    f"  [{flag}] {label:11} k={k}  loss={sol.loss:.5f} "
                    f"(exact={exact_sol.loss:.5f}, {hit_flag}, jaccard={jacc:.2f})"
                )
                if not consistent:
                    print(
                        f"        ! loss != recomputed delta_k ({sol.loss} vs {float(recomputed)})"
                    )
                if not lower_bounded:
                    print("        ! loss is below the exact optimum (impossible)")
            except Exception as err:
                print(f"  [ERR] {label:11} k={k}  {type(err).__name__}: {err}")

    return passed, total


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-strategy correctness validation")
    parser.add_argument("--nets", nargs="*", default=["N3A", "N3B", "N4A", "N4B", "N5B"])
    parser.add_argument("--ks", nargs="*", type=int, default=[2, 3])
    args = parser.parse_args()
    application.disable_profiling()

    total_passed = total_all = 0
    for net in args.nets:
        try:
            p, t = validate_net(net, args.ks)
        except FileNotFoundError:
            print(f"\n=== {net}: (sample not found) ===")
            continue
        total_passed += p
        total_all += t

    print(f"\n{'=' * 40}\nTOTAL: {total_passed}/{total_all} checks passed")
    sys.exit(0 if total_passed == total_all else 1)


if __name__ == "__main__":
    main()
