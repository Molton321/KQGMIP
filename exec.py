"""
Punto de entrada principal del framework IIT.

Uso:
    uv run exec.py              → análisis individual (main.py)
    uv run exec.py --batch      → procesamiento por lotes desde Excel (main_batch.py)

Configuraciones de la aplicación disponibles en src/base/application.py.
"""

import sys
from src.base.application import aplicacion


def main():
    aplicacion.activar_profiling()
    aplicacion.set_pagina_red_muestra("A")

    if "--batch" in sys.argv:
        from main_batch import iniciar
    else:
        from main import iniciar

    iniciar()


if __name__ == "__main__":
    main()
