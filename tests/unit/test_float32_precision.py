"""Validate the float32 n-cube storage against a float64 reference (Phase 6).

The n-cube tensors are stored as float32 for speed/memory. For the deterministic
0/1 TPMs used here the marginal means are dyadic, so float32 is exact at small
sizes (covered by the strict k=2 regression). This test additionally bounds the
float32-vs-float64 deviation of the end-to-end loss at mid sizes (n=10, 15),
where no exact oracle exists, by temporarily rebuilding the cubes in float64.
"""

import contextlib
import io

import numpy as np
import pytest

import src.models.core.system as system_mod
from src.controllers.manager import Manager
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.kqnodes import KQNodes
from src.models.base.application import application


@pytest.fixture
def restore_dtype():
    original = system_mod.NCUBE_DTYPE
    yield
    system_mod.NCUBE_DTYPE = original


def _loss(net: str, strategy_cls, k: int, dtype: type = np.float32) -> float:
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    # Load the raw TPM at the requested precision so the float64 path is a
    # genuine reference (Manager.load_network now loads float32 in production).
    tpm = np.genfromtxt(Manager(state).tpm_filename, delimiter=",", dtype=dtype)
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return strategy_cls(tpm, state, k=k).apply_strategy(full, full, full).loss


def test_ncube_marginal_is_float32() -> None:
    tpm = Manager("1" * 4).load_network()
    system = system_mod.System(tpm, np.array([1, 1, 1, 1], dtype=np.int8))
    cube = system.ncubes[0]
    assert cube.marginal_value(cube.dims, system.initial_state, True).dtype == np.float32


@pytest.mark.parametrize("net, strategy, k", [("N10A", KGeoMIP, 3), ("N15A", KQNodes, 2)])
def test_float32_loss_matches_float64(net, strategy, k, restore_dtype) -> None:
    """float32 end-to-end loss stays within a tight bound of the float64 result."""
    system_mod.NCUBE_DTYPE = np.float32
    loss32 = _loss(net, strategy, k, dtype=np.float32)
    system_mod.NCUBE_DTYPE = np.float64
    loss64 = _loss(net, strategy, k, dtype=np.float64)
    assert loss32 == pytest.approx(loss64, abs=1e-5)


def test_float32_loss_on_continuous_tpm(tmp_path, restore_dtype) -> None:
    """float32 stays within bound on a *continuous* TPM, not only 0/1 values.

    The 0/1 nets above are exact in float32; this covers the harder case where
    the marginal means are non-dyadic (continuous probabilities in [0, 1]).
    """
    state = "1" * 10
    application.set_sample_network_page("A")
    manager = Manager(state, base_path=tmp_path)
    with contextlib.redirect_stdout(io.StringIO()):
        manager.generate_network(10, deterministic=False)
    path = manager.tpm_filename

    losses = {}
    for dtype in (np.float32, np.float64):
        system_mod.NCUBE_DTYPE = dtype
        tpm = np.genfromtxt(path, delimiter=",", dtype=dtype)
        with contextlib.redirect_stdout(io.StringIO()):
            losses[dtype] = KGeoMIP(tpm, state, k=2).apply_strategy(state, state, state).loss
    assert losses[np.float32] == pytest.approx(losses[np.float64], abs=1e-5)
