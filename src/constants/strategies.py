"""Centralized strategy labels and logging/profiling tags.

One place defining the display label and the ``*_strategy`` / ``*_analysis`` tags
for every strategy, so no strategy module hard-codes its own name strings.
"""

CLUSTERING_LABEL: str = "Clustering"
CLUSTERING_STRATEGY_TAG: str = f"{CLUSTERING_LABEL}_strategy"
CLUSTERING_ANALYSIS_TAG: str = f"{CLUSTERING_LABEL}_analysis"
MAX_AFFINITY_SAMPLE: int = 4096

EXACT_K_LABEL: str = "ExactK"
EXACT_K_STRATEGY_TAG: str = f"{EXACT_K_LABEL}_strategy"

BRUTEFORCE_LABEL: str = "BruteForce"
BRUTEFORCE_STRATEGY_TAG: str = f"{BRUTEFORCE_LABEL}_strategy"
BRUTEFORCE_ANALYSIS_TAG: str = f"{BRUTEFORCE_LABEL}_analysis"

GEOMETRIC_LABEL: str = "Geometric"
GEOMETRIC_STRATEGY_TAG: str = f"{GEOMETRIC_LABEL}_strategy"
GEOMETRIC_ANALYSIS_TAG: str = f"{GEOMETRIC_LABEL}_analysis"


KGEOMIP_LABEL: str = "KGeoMIP"
KGEOMIP_STRATEGY_TAG: str = f"{KGEOMIP_LABEL}_strategy"
KGEOMIP_ANALYSIS_TAG: str = f"{KGEOMIP_LABEL}_analysis"


KQNODES_LABEL: str = "KQNodes"
KQNODES_STRATEGY_TAG: str = f"{KQNODES_LABEL}_strategy"
KQNODES_ANALYSIS_TAG: str = f"{KQNODES_LABEL}_analysis"


PYPHI_LABEL: str = "Pyphi"
PYPHI_STRATEGY_TAG: str = f"{PYPHI_LABEL}_strategy"
PYPHI_ANALYSIS_TAG: str = f"{PYPHI_LABEL}_analysis"


QNODES_LABEL: str = "Q-Nodes"
QNODES_STRATEGY_TAG: str = f"{QNODES_LABEL}_strategy"
QNODES_ANALYSIS_TAG: str = f"{QNODES_LABEL}_analysis"
