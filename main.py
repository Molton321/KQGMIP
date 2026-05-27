"""
Punto de entrada para análisis de un único subsistema.

Configura los parámetros ABCD del sistema y elige la estrategia:
  - BruteForce   → fuerza bruta (exacta, exponencial)
  - QNodes       → greedy submodular (rápida, polinomial)
  - Phi          → librería pyphi de referencia
  - GeometricSIA → programación dinámica geométrica (GeoMIP)
"""

from src.io.manager import Manager
from src.strategies.brute_force import BruteForce
# from src.strategies.q_nodes import QNodes
# from src.strategies.pyphi_wrapper import Phi
# from src.strategies.geometric import GeometricSIA


def iniciar():
    # ── Parámetros del subsistema ──────────────────────────────────────────
    # Cada cadena tiene un bit por nodo (0 = excluir, 1 = incluir).
    estado_inicial = "1000"   # Estado en t=0
    condiciones    = "1110"   # Condiciones de fondo: 0 → condicionar variable
    alcance        = "1110"   # Alcance futuro:       0 → marginalizar variable
    mecanismo      = "1110"   # Mecanismo presente:   0 → marginalizar variable
    # ───────────────────────────────────────────────────────────────────────

    gestor = Manager(estado_inicial)
    tpm = gestor.cargar_red()

    analizador = BruteForce(tpm, estado_inicial)
    solucion = analizador.aplicar_estrategia(condiciones, alcance, mecanismo)
    print(solucion)
