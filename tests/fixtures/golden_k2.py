"""Golden k=2 oracle values for the regression suite.

``ORACLE_LOSS`` is the minimum-information-partition loss (φ) for the full
subsystem (all-ones initial state and masks) of each network. These values were
cross-validated on 2026-06-09 against the original reference project
(``.core/core_00/QNodes`` ``BruteForce``): the reference's BruteForce reproduces
every value here exactly (10/10), so this table is the legacy ground truth that
Invariant 1 (k=2 must reproduce GeoMIP/QNodes) is checked against.

``QNODES_LOSS`` records the *legacy* QNodes behaviour, including its single known
suboptimal case (``QNODES_SUBOPTIMAL``): N3B, where the historical QNodes returns
0.5 instead of the optimal 0.46875. The defect is frozen here on purpose.
"""

NETS = ["N2A", "N3A", "N3B", "N3C", "N4A", "N4B", "N4C", "N5A", "N5B", "N6A"]

ORACLE_LOSS = {
    "N2A": 0.0,
    "N3A": 0.25,
    "N3B": 0.46875,
    "N3C": 0.0,
    "N4A": 0.0,
    "N4B": 0.0,
    "N4C": 0.0,
    "N5A": 0.0,
    "N5B": 0.125,
    "N6A": 0.46875,
}

QNODES_LOSS = {
    "N2A": 0.0,
    "N3A": 0.25,
    "N3B": 0.5,
    "N3C": 0.0,
    "N4A": 0.0,
    "N4B": 0.0,
    "N4C": 0.0,
    "N5A": 0.0,
    "N5B": 0.125,
    "N6A": 0.46875,
}

QNODES_SUBOPTIMAL = ["N3B"]
