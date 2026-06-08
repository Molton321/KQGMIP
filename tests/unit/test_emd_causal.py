"""Tests for the optional causal EMD path (requires the ``pyemd`` package).

The project's δ_k uses the analytic effect EMD; the causal EMD (Hamming-ground
Earth Mover's Distance via ``pyemd``) is an optional alternative metric for
cross-checking. These tests are skipped when ``pyemd`` is not installed.
"""

import numpy as np
import pytest

pyemd = pytest.importorskip("pyemd")  # noqa: F841  (skip whole module if missing)

from src.funcs.emd import causal_emd, effect_emd, select_emd  # noqa: E402
from src.models.base.application import application  # noqa: E402
from src.models.enums.temporal_emd import TimeEMD  # noqa: E402


def test_causal_emd_zero_for_identical() -> None:
    """EMD between identical distributions is zero."""
    u = np.array([0.25, 0.25, 0.25, 0.25])
    assert causal_emd(u, u.copy()) == pytest.approx(0.0, abs=1e-9)


def test_causal_emd_is_nonnegative_and_symmetric() -> None:
    u = np.array([1.0, 0.0, 0.0, 0.0])
    v = np.array([0.0, 0.0, 0.0, 1.0])
    duv = causal_emd(u, v)
    dvu = causal_emd(v, u)
    assert duv >= 0.0
    assert duv == pytest.approx(dvu, abs=1e-9)


def test_select_emd_dispatches_to_cause() -> None:
    """``application.emd_time = EMD_CAUSE`` selects the causal metric."""
    previous = application.emd_time
    try:
        application.set_emd_time(TimeEMD.EMD_CAUSE)
        assert select_emd() is causal_emd
        application.set_emd_time(TimeEMD.EMD_EFFECT)
        assert select_emd() is effect_emd
    finally:
        application.emd_time = previous
