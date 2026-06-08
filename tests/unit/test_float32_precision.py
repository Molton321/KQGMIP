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


def _loss(net: str, strategy_cls, k: int) -> float:
    n = int(net[1:-1])
    application.set_sample_network_page(net[-1])
    state = "1" * n
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        return strategy_cls(tpm, state, k=k).apply_strategy(full, full, full).loss


def test_ncube_dtype_is_float32() -> None:
    tpm = Manager("1" * 4).load_network()
    system = system_mod.System(tpm, np.array([1, 1, 1, 1], dtype=np.int8))
    assert system.ncubes[0].data.dtype == np.float32


@pytest.mark.parametrize("net, strategy, k", [("N10A", KGeoMIP, 3), ("N15A", KQNodes, 2)])
def test_float32_loss_matches_float64(net, strategy, k, restore_dtype) -> None:
    """float32 end-to-end loss stays within a tight bound of the float64 result."""
    system_mod.NCUBE_DTYPE = np.float32
    loss32 = _loss(net, strategy, k)
    system_mod.NCUBE_DTYPE = np.float64
    loss64 = _loss(net, strategy, k)
    assert loss32 == pytest.approx(loss64, abs=1e-5)
