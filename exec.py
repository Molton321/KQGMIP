"""
K-QGMIP CLI: run a single analysis or a batch of analyses with the same strategy and k.
"""

import argparse
import os
import sys

from main_batch import run
from src.funcs.runner import load_tpm, parse_net_label, run_analysis
from src.models.base.application import application


class ExecApp:
    _STRATEGY_CHOICES = sorted(
        k.lower()
        for k in [
            "KGeoMIP",
            "KQNodes",
            "Clustering",
            "Genetic",
            "Annealing",
            "Tabu",
            "ExhaustiveK",
        ]
    )
    _METHOD_CHOICES = ["spectral", "kmeans"]
    _EPILOG = (
        "Estrategias: kgeomip, kqnodes, clustering, genetic, annealing, tabu, exhaustive. "
        "Método clustering: spectral, kmeans."
    )

    def __init__(self) -> None:
        self._parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> None:
        args = self._parser.parse_args(argv)
        self._configure_profiling(args)
        if args.batch:
            self._run_batch(args)
        elif args.net:
            self._run_single(args)
        else:
            self._run_demo()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="exec.py",
            description="Análisis de k-particiones de mínima información (IIT).",
            epilog=self._EPILOG,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("--net", help="Red a analizar, p. ej. N10A (define n y página).")
        parser.add_argument("--k", type=int, default=3, help="Número de bloques (k >= 2).")
        parser.add_argument("--strategy", default="kgeomip", choices=self._STRATEGY_CHOICES)
        parser.add_argument("--page", help="Página de la red (A, B, ...).")
        parser.add_argument(
            "--state",
            help="Estado inicial binario, p. ej. 1000 (por defecto todo en 1).",
        )
        parser.add_argument("--method", default="spectral", choices=self._METHOD_CHOICES)
        parser.add_argument("--condition")
        parser.add_argument("--purview")
        parser.add_argument("--mechanism")
        parser.add_argument("--profile", action="store_true")
        parser.add_argument("--batch", action="store_true")
        return parser

    def _configure_profiling(self, args: argparse.Namespace) -> None:

        if args.profile:
            application.enable_profiling()
        else:
            application.disable_profiling()

    def _run_single(self, args: argparse.Namespace) -> None:
        n, default_page, default_state = parse_net_label(args.net.upper())
        state = args.state or default_state
        if len(state) != n:
            self._parser.error(
                f"--state debe tener {n} dígitos para {args.net.upper()} (recibido: {state!r})."
            )
        page = args.page or default_page
        tpm = load_tpm(state, page)
        result = run_analysis(
            tpm,
            state,
            args.strategy,
            args.k,
            method=args.method,
            condition=args.condition,
            purview=args.purview,
            mechanism=args.mechanism,
        )
        print(result.solution)

    def _run_batch(self, args: argparse.Namespace) -> None:
        application.set_sample_network_page(args.page or "A")
        os.environ.setdefault("IIT_STRATEGY", args.strategy)
        os.environ.setdefault("IIT_K", str(args.k))
        os.environ.setdefault("IIT_METHOD", args.method)
        sys.argv = ["main_batch.py"]

        run()

    def _run_demo(self) -> None:

        print(__doc__)
        print("=" * 70)
        print("Demostración: KGeoMIP, k=3, N10A\n")
        tpm = load_tpm("1" * 10, "A")
        result = run_analysis(tpm, "1" * 10, "kgeomip", 3)
        print(result.solution)


def _main() -> None:
    ExecApp().run()


if __name__ == "__main__":
    _main()
