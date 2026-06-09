"""Render k-partition visualizations for the demo (Phase 7).

Runs a strategy on a small network and renders its best k-partition both as a
layered block diagram and (for n<=4) as a node-hypercube projection.

    uv run scripts/make_viz.py
    uv run scripts/make_viz.py --net N4A --k 3 --strategy KGeoMIP
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# isort: split
from src.controllers.manager import Manager
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.kqnodes import KQNodes
from src.models.base.application import application
from src.viz import plot_hypercube_partition, plot_kpartition

STRATEGIES = {"KGeoMIP": KGeoMIP, "KQNodes": KQNodes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Render k-partition figures")
    parser.add_argument("--net", default="N4A")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--strategy", default="KGeoMIP", choices=list(STRATEGIES))
    parser.add_argument("--out", default="data/results/figures")
    args = parser.parse_args()

    application.disable_profiling()
    n = int(args.net[1:-1])
    application.set_sample_network_page(args.net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n

    analyzer = STRATEGIES[args.strategy](tpm, state, k=args.k)
    with contextlib.redirect_stdout(io.StringIO()):
        analyzer.apply_strategy(full, full, full)
    partition = analyzer.best_partition
    if partition is None:
        print("No partition produced.")
        sys.exit(1)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"{args.strategy}_{args.net}_k{args.k}"
    title = f"{args.strategy} {args.net} k={args.k}"
    p1 = plot_kpartition(partition, f"{title} — block diagram", str(out / f"partition_{base}.png"))
    p2 = plot_hypercube_partition(
        partition, f"{title} — hypercube", str(out / f"hypercube_{base}.png")
    )
    print(f"Wrote:\n  - {p1}\n  - {p2}")


if __name__ == "__main__":
    main()
