"""Generate a TPM sample network from the command line.

Usage:
    uv run scripts/generate_tpm.py --n 4
    uv run scripts/generate_tpm.py --n 6 --continuous
    uv run scripts/generate_tpm.py --n 10 --seed 7 --yes
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.controllers.manager import Manager
from src.models.base.application import application


def main() -> None:
    parser = argparse.ArgumentParser(description="Generar una TPM de muestra (CSV).")
    parser.add_argument("--n", type=int, required=True, help="número de nodos")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="probabilidades continuas en vez de 0/1 deterministas",
    )
    parser.add_argument(
        "--seed", type=int, default=application.numpy_seed, help="semilla NumPy"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="modo no interactivo (acepta tamaños grandes y autoincrementa el sufijo)",
    )
    args = parser.parse_args()

    application.numpy_seed = args.seed
    filename = Manager("1" * args.n).generate_network(
        args.n, deterministic=not args.continuous, assume_yes=args.yes
    )
    if filename:
        print(f"OK: {filename}")
    else:
        print("Generación cancelada.")
        sys.exit(1)


if __name__ == "__main__":
    main()
