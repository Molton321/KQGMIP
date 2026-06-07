"""Isolated micro-benchmarks for Phase 6 (efficiency / PCD).

Run with the profiler **disabled** so the measured time reflects the real work,
not the instrumentation:

    uv run scripts/bench_fase6.py
    uv run --extra perf scripts/bench_fase6.py   # also exercises the Numba path

Each measurement reports the **minimum** wall-clock time over several repetitions
(the minimum is the most stable estimator: it filters out scheduler/GC noise).
The harness covers two layers:

- core kernels (``NCube.marginalize``, ``System.marginal_distribution``,
  ``System.bipartition``) in isolation, and
- the end-to-end strategies (KGeoMIP / KQNodes / clustering / exact).

It is a developer tool (not shipped in ``src``), used to demonstrate the speedup
of each optimization against a captured baseline.
"""

import contextlib
import io
import os
import sys
import time
from collections.abc import Callable

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.controllers.manager import Manager
from src.models.base.application import application
from src.models.core.system import System


def _timeit(fn: Callable[[], object], reps: int = 5) -> float:
    """Return the minimum wall-clock time of ``fn`` over ``reps`` runs."""
    best = float("inf")
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


def _load(net: str) -> tuple[np.ndarray, str]:
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    return Manager(state).load_network(), state


def _full_system(net: str) -> System:
    tpm, state = _load(net)
    return System(tpm, np.array([int(b) for b in state], dtype=np.int8))


def bench_kernels(nets: list[str]) -> None:
    """Benchmark the shared core kernels in isolation."""
    print("\n== core kernels (min time over reps) ==")
    for net in nets:
        try:
            system = _full_system(net)
        except FileNotFoundError:
            print(f"  {net}: (no sample)")
            continue
        dims = system.ncube_dims
        mechanism = dims[: max(1, dims.size // 2)]
        purview = system.ncube_indices[: max(1, system.ncube_indices.size // 2)]

        def cold_marginalize(s=system, m=dims):
            # marginalize() is memoized; clear the cache to time the real compute.
            s.ncubes[0].memo.clear()
            return s.ncubes[0].marginalize(m)

        def cold_bipartition(s=system, p=purview, m=mechanism):
            s.memo.clear()
            return s.bipartition(p, m).marginal_distribution()

        reps = 20 if system.ncube_dims.size <= 16 else 3
        t_marg = _timeit(cold_marginalize, reps=reps)
        t_dist = _timeit(lambda s=system: s.marginal_distribution(), reps=reps)
        t_bip = _timeit(cold_bipartition, reps=reps)
        print(
            f"  {net}: marginalize={t_marg * 1e3:.3f}ms  "
            f"marginal_dist={t_dist * 1e3:.3f}ms  bipartition={t_bip * 1e3:.3f}ms"
        )


def bench_strategies(cases: list[tuple[str, int]]) -> None:
    """Benchmark end-to-end strategies (profiler must be disabled)."""
    from src.controllers.strategies.clustering import ClusteringSIA
    from src.controllers.strategies.exhaustive_k import ExhaustiveK
    from src.controllers.strategies.kgeomip import KGeoMIP
    from src.controllers.strategies.kqnodes import KQNodes

    print("\n== strategies end-to-end (min time over reps) ==")
    for net, k in cases:
        try:
            tpm, state = _load(net)
        except FileNotFoundError:
            print(f"  {net} k={k}: (no sample)")
            continue
        full = "1" * int(net[1:-1])

        def run(cls, kk=k, t=tpm, s=state, f=full):
            with contextlib.redirect_stdout(io.StringIO()):
                cls(t, s, k=kk).apply_strategy(f, f, f)

        n = int(net[1:-1])
        row = [f"  {net} k={k}:"]
        # Size caps keep the harness fast: the geometric/submodular searches are
        # superlinear, the exact search is exponential, clustering is cheap.
        for label, cls, max_n in [
            ("KGeoMIP", KGeoMIP, 12),
            ("KQNodes", KQNodes, 10),
            ("Cluster", ClusteringSIA, 25),
            ("Exact", ExhaustiveK, 6),
        ]:
            if n > max_n:
                continue
            try:
                row.append(f"{label}={_timeit(lambda c=cls: run(c), reps=2) * 1e3:.1f}ms")
            except Exception as err:  # pragma: no cover - benchmarking aid
                row.append(f"{label}=ERR({type(err).__name__})")
        print("  ".join(row))


def bench_parallel(net: str = "N6A", k: int = 3) -> None:
    """Sequential vs process-parallel exact search (PCD speedup demonstration).

    Slow (the sequential exact search is exponential), so it only runs when the
    harness is invoked as ``uv run scripts/bench_fase6.py parallel``.
    """
    from src.controllers.strategies.exhaustive_k import ExhaustiveK

    print(f"\n== ExhaustiveK {net} k={k}: sequential vs parallel ==")
    tpm, state = _load(net)
    full = "1" * int(net[1:-1])

    def run(parallel: bool):
        with contextlib.redirect_stdout(io.StringIO()):
            return ExhaustiveK(tpm, state, k=k, parallel=parallel).apply_strategy(full, full, full)

    t_seq = _timeit(lambda: run(False), reps=1)
    t_par = _timeit(lambda: run(True), reps=1)
    print(
        f"  sequential={t_seq:.1f}s  parallel({os.cpu_count()})={t_par:.1f}s  "
        f"speedup={t_seq / t_par:.1f}x"
    )


def main() -> None:
    application.disable_profiling()
    try:
        from src.funcs import accelerate

        print(f"acceleration backend: {accelerate.BACKEND}")
    except Exception:
        print("acceleration backend: (accelerate module unavailable)")

    bench_kernels(["N10A", "N15A", "N20A"])
    bench_strategies([("N6A", 3), ("N10A", 3), ("N15A", 3)])
    if "parallel" in sys.argv:
        bench_parallel()


if __name__ == "__main__":
    main()
