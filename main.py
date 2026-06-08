"""
Análisis individual configurando el código (ruta avanzada/manual).

La mayoría de usuarios NO necesita este archivo: la forma fácil es la interfaz web
(``uv run streamlit run streamlit_app.py``) o las banderas de ``exec.py``
(``uv run exec.py --net N10A --k 3 --strategy kgeomip``), sin editar código.

Este archivo se mantiene para quien quiera fijar a mano el subsistema (estado,
condición, purview, mecanismo) y la estrategia. Editar los valores de abajo y:

    uv run main.py
"""

from src.funcs.runner import load_tpm, run_analysis
from src.models.base.application import application

# ═══════════════════════════════════════════════════════════════════════════════
# Parámetros del subsistema (1 bit por nodo; 0 = excluir/condicionar)
# ═══════════════════════════════════════════════════════════════════════════════

initial_state = "1111011011"  # Estado en t=0 (10 nodos)
conditions = "1110001100"     # 0 = condicionar (fijar) la variable
purview = "0011101111"        # 0 = marginalizar el nodo futuro
mechanism = "1000111111"      # 0 = marginalizar el nodo presente
k = 3                         # Número de particiones (k >= 2)

# Estrategia (cualquier nombre del registro src/funcs/runner.py): kgeomip, kqnodes,
# clustering, genetic, annealing, tabu, exhaustive, y las legadas k=2 geometric/qnodes.
STRATEGY_NAME = "kgeomip"
PAGE = "A"                    # Página de red (A, B, C, ...)
METHOD = "spectral"           # Método de clustering (solo estrategia clustering)


def run():
    application.set_sample_network_page(PAGE)
    tpm = load_tpm(initial_state, PAGE)
    result = run_analysis(
        tpm, initial_state, STRATEGY_NAME, k,
        method=METHOD, condition=conditions, purview=purview, mechanism=mechanism,
    )
    print(result.solution)


if __name__ == "__main__":
    run()
