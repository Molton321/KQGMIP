"""Single entry point for every validation of the system (spec §4.3).

Subcommands (each forwards its remaining options to the underlying module):

    uv run scripts/validate.py correctness [--nets ... --ks ...]
        Every strategy vs the exact optimum on small networks: loss/partition
        consistency, exact-hit rate and the lower-bound invariant.

    uv run scripts/validate.py optimality [--nets ... --ks ...]
        Optimality evidence at scale: exact where feasible, convergence of
        independent strategies elsewhere.

    uv run scripts/validate.py external [--docente-rows N | --verify-partitions ...]
        Cross-validation against the professor's original project
        (.core/core_00): byte-identical TPM samples, reproduction of the
        original GeoMIP results, and re-evaluation of every stored partition of
        the results workbook with the official delta_k.
"""

import runpy
import sys
from pathlib import Path

MODULES = {
    "correctness": "correctness.py",
    "optimality": "optimality.py",
    "external": "external.py",
}


def main() -> None:
    """Dispatch the chosen validation module with the forwarded argv."""
    if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
        print(__doc__)
        raise SystemExit(0 if len(sys.argv) >= 2 and sys.argv[1] in ("-h", "--help") else 2)
    target = Path(__file__).resolve().parent / "validation" / MODULES[sys.argv[1]]
    sys.argv = [str(target), *sys.argv[2:]]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
