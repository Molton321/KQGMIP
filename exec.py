"""Punto de entrada del framework K-QGMIP.

Tres formas de usarlo (de la más fácil a la más avanzada):

1. Interfaz web (recomendada, sin escribir comandos largos):
       uv run streamlit run streamlit_app.py

2. Análisis por banderas (sin editar código):
       uv run exec.py --net N10A --k 3 --strategy kgeomip
       uv run exec.py --net N4A  --k 2 --strategy kqnodes
   Estrategias: kgeomip, kqnodes, clustering, genetic, annealing, tabu, exhaustive.
   Opcionales: --page B, --method kmeans (clustering), --condition/--purview/--mechanism,
   --profile (activa los reportes HTML, desactivados por defecto).

3. Lote desde Excel (rejilla de subsistemas):
       uv run exec.py --batch --strategy kqnodes --k 4

Sin argumentos ejecuta una demostración (KGeoMIP, k=3, N10A) y muestra esta ayuda.
"""

import argparse

from src.funcs.runner import STRATEGY_BUILDERS
from src.models.base.application import application

# Las estrategias seleccionables vienen del único registro (src/funcs/runner.py).
_STRATEGY_CHOICES = sorted(key.lower() for key in STRATEGY_BUILDERS)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exec.py", description="Análisis de k-particiones de mínima información (IIT).",
    )
    parser.add_argument("--net", help="Red a analizar, p. ej. N10A (define n y página).")
    parser.add_argument("--k", type=int, default=3, help="Número de bloques (k >= 2). Por defecto 3.")
    parser.add_argument(
        "--strategy", default="kgeomip", choices=_STRATEGY_CHOICES,
        help="Estrategia a usar. Por defecto kgeomip.",
    )
    parser.add_argument("--page", help="Página de la red (A, B, ...). Por defecto, la de --net.")
    parser.add_argument("--method", default="spectral", choices=["spectral", "kmeans"],
                        help="Método de clustering (solo estrategia clustering).")
    parser.add_argument("--condition", help="Máscara de condición de fondo (por defecto, todo activo).")
    parser.add_argument("--purview", help="Máscara de purview/futuro (por defecto, todo activo).")
    parser.add_argument("--mechanism", help="Máscara de mecanismo/presente (por defecto, todo activo).")
    parser.add_argument("--profile", action="store_true", help="Activa el profiling (HTML en review/).")
    parser.add_argument("--batch", action="store_true", help="Procesa una rejilla de subsistemas desde Excel.")
    return parser


def _run_single(args: argparse.Namespace) -> None:
    """Ejecuta una sola estrategia por banderas y muestra el resultado."""
    from src.funcs.runner import load_tpm, parse_net_label, run_analysis

    _, default_page, state = parse_net_label(args.net.upper())
    page = args.page or default_page
    tpm = load_tpm(state, page)
    result = run_analysis(
        tpm, state, args.strategy, args.k,
        method=args.method, condition=args.condition,
        purview=args.purview, mechanism=args.mechanism,
    )
    print(result.solution)


def main() -> None:
    args = _build_parser().parse_args()

    # El profiling se desactiva por defecto (medición limpia, sin reportes HTML).
    if args.profile:
        application.enable_profiling()
    else:
        application.disable_profiling()

    if args.batch:
        application.set_sample_network_page(args.page or "A")
        # Puente banderas -> variables de entorno que lee main_batch.run().
        import os
        os.environ.setdefault("IIT_STRATEGY", args.strategy)
        os.environ.setdefault("IIT_K", str(args.k))
        os.environ.setdefault("IIT_METHOD", args.method)
        from main_batch import run
        run()
        return

    if args.net:
        _run_single(args)
        return

    # Sin argumentos: demostración + ayuda breve.
    print(__doc__)
    print("=" * 70)
    print("Demostración: KGeoMIP, k=3, N10A\n")
    args.net, args.strategy, args.k = "N10A", "kgeomip", 3
    _run_single(args)


if __name__ == "__main__":
    main()
