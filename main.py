"""
Entry point for the analysis of a single subsystem.

Sets the system's ABCD parameters and chooses the strategy:
  - BruteForce   → brute force (exact, exponential)
  - QNodes       → greedy submodular (fast, polynomial)
  - Phi          → reference pyphi library
  - GeometricSIA → geometric dynamic programming (GeoMIP)
"""

from src.controllers.manager import Manager
from src.controllers.strategies.q_nodes import QNodes

# from src.controllers.strategies.phi import Phi
# from src.controllers.strategies.geometric import GeometricSIA


def run():
    # ── Subsystem parameters ───────────────────────────────────────────────
    # Each string holds one bit per node (0 = exclude, 1 = include).
    initial_state = "1111011011"  # State at t=0
    conditions = "1110001100"  # Background conditions: 0 → condition the variable
    purview = "0011101111"  # Future purview:        0 → marginalize the variable
    mechanism = "1000111111"  # Present mechanism:     0 → marginalize the variable

    # ───────────────────────────────────────────────────────────────────────

    manager = Manager(initial_state)
    tpm = manager.load_network()

    analyzer = QNodes(tpm, initial_state)
    solution = analyzer.apply_strategy(conditions, purview, mechanism)
    print(solution)
