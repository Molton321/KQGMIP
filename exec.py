"""K-QGMIP CLI: single analyses, batch table filling, results viewing and benchmarks.

Offers the same actions as the web UI over the standard *-Elementos xlsx
format (datos.xlsx in, resultados.xlsx out by default).
"""

import argparse
import subprocess
import sys
from pathlib import Path

from src.constants.base import PROJECT_ROOT
from src.constants.grid import GRID_RESULTS_XLSX, GRID_TEMPLATE_XLSX
from src.funcs.grid import fill_grid, format_results_text, grid_sheet_names, read_grid_results
from src.funcs.runner import load_tpm, parse_net_label, run_analysis
from src.models.base.application import application

USAGE_ES = """\
K-QGMIP: análisis de k-particiones de mínima información (IIT).

Comandos (los mismos que ofrece la interfaz web):
    uv run exec.py                                  → demostración + ayuda
    uv run exec.py run --net N10A --k 3             → un análisis individual
    uv run exec.py batch [file.xlsx]             → llenar la tabla de evaluación
    uv run exec.py results [file.xlsx]        → ver la tabla de resultados
    uv run exec.py benchmark [--quick]              → regenerar el benchmark δ_k vs k
"""


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

    def __init__(self) -> None:
        self._parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> None:
        """Dispatch the parsed subcommand."""
        args = self._parser.parse_args(argv)
        if args.profile:
            application.enable_profiling()
        else:
            application.disable_profiling()

        if args.command == "run":
            self._run_single(args)
        elif args.command == "batch":
            self._run_batch(args)
        elif args.command == "results":
            self._show_results(args)
        elif args.command == "benchmark":
            self._run_benchmark(args)
        else:
            self._run_demo()

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build the subcommand parser (run / batch / results / benchmark)."""
        parser = argparse.ArgumentParser(
            prog="exec.py",
            description=USAGE_ES,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--profile", action="store_true", help="Activa el profiler."
        )
        commands = parser.add_subparsers(dest="command")

        single = commands.add_parser("run", help="Un análisis individual.")
        single.add_argument("--net", required=True, help="Red, p. ej. N10A.")
        single.add_argument("--k", type=int, default=3, help="Bloques (k >= 2).")
        single.add_argument(
            "--strategy", default="kgeomip", choices=self._STRATEGY_CHOICES
        )
        single.add_argument("--page", help="Página de la red (A, B, ...).")
        single.add_argument("--state", help="Estado inicial binario (defecto: todo 1).")
        single.add_argument(
            "--method", default="spectral", choices=self._METHOD_CHOICES
        )
        single.add_argument("--condition")
        single.add_argument("--purview")
        single.add_argument("--mechanism")

        batch = commands.add_parser(
            "batch", help="Llenar la tabla de evaluación (formato estándar)."
        )
        batch.add_argument(
            "file",
            nargs="?",
            help=f"Workbook con hojas *-Elementos (defecto: {GRID_TEMPLATE_XLSX.name}).",
        )
        batch.add_argument(
            "--out", help="Workbook de resultados (nunca pisa la entrada)."
        )
        batch.add_argument("--sheets", nargs="*", default=None, help="Hojas a llenar.")

        results = commands.add_parser(
            "results", help="Ver una tabla de resultados en la terminal."
        )
        results.add_argument(
            "file",
            nargs="?",
            help=f"Workbook de resultados (defecto: {GRID_RESULTS_XLSX.name}).",
        )
        results.add_argument(
            "--complete",
            action="store_true",
            help="Muestra todas las filas (sin recorte).",
        )

        benchmark = commands.add_parser(
            "benchmark",
            help="Regenerar el benchmark δ_k (alimenta la sección de la web).",
        )
        benchmark.add_argument(
            "--quick", action="store_true", help="Solo N10A (rápido)."
        )
        benchmark.add_argument(
            "--nets", nargs="*", default=None, help="Redes, p. ej. N10A N15A."
        )
        return parser

    @staticmethod
    def _resolve_input(candidate: str | None, default: Path) -> Path:
        """Pick the workbook to use (explicit path or the configured default)."""
        if candidate:
            path = Path(candidate)
            if not path.exists():
                raise SystemExit(f"No existe el archivo: {path}")
            return path
        if default.exists():
            return default
        raise SystemExit(
            f"No se encontró {default}. "
            "Indica un archivo .xlsx con el formato estándar (hojas *-Elementos)."
        )

    def _run_single(self, args: argparse.Namespace) -> None:
        """Run one strategy over one subsystem and print the solution."""
        n, default_page, default_state = parse_net_label(args.net.upper())
        state = args.state or default_state
        if len(state) != n:
            self._parser.error(
                f"--state debe tener {n} dígitos para {args.net.upper()} (recibido: {state!r})."
            )
        tpm = load_tpm(state, args.page or default_page)
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
        """Fill every missing cell of a standard workbook (resumable)."""
        source = self._resolve_input(args.archivo, GRID_TEMPLATE_XLSX)
        if not grid_sheet_names(source):
            raise SystemExit(
                f"{source} no tiene hojas '*-Elementos': no cumple el formato estándar."
            )
        output = Path(args.salida) if args.salida else GRID_RESULTS_XLSX
        if output.resolve() == source.resolve():
            raise SystemExit("La salida no puede ser el mismo archivo de entrada.")
        print(
            f"Entrada: {source}\nSalida:  {output} (reanudable; la entrada no se modifica)\n"
        )
        fill_grid(source, output, sheet_names=args.hojas)
        print(f"\nPara ver la tabla: uv run exec.py results {output}")

    def _show_results(self, args: argparse.Namespace) -> None:
        """Print the console view of a results workbook."""
        source = self._resolve_input(args.archivo, GRID_RESULTS_XLSX)
        rows = read_grid_results(source)
        print(f"Archivo: {source}")
        print(format_results_text(rows, max_rows=None if args.completo else 24))

    def _run_benchmark(self, args: argparse.Namespace) -> None:
        """Delegate to the benchmark script with the same interpreter."""
        command = [sys.executable, str(PROJECT_ROOT / "scripts" / "run_benchmark.py")]
        if args.quick:
            command.append("--quick")
        if args.nets:
            command.extend(["--nets", *args.nets])
        raise SystemExit(subprocess.run(command, check=False).returncode)

    def _run_demo(self) -> None:
        """Print the usage guide and run a small example end to end."""
        print(USAGE_ES)
        print("=" * 70)
        print("Demostración: KGeoMIP, k=3, N10A\n")
        tpm = load_tpm("1" * 10, "A")
        result = run_analysis(tpm, "1" * 10, "kgeomip", 3)
        print(result.solution)


def _main() -> None:
    ExecApp().run()


if __name__ == "__main__":
    _main()
