"""Memory-oriented TPM dtype handling must never change numeric results.

Deterministic 0/1 TPMs load as uint8 (4x smaller resident memory) and are cast
to float32 per cube inside ``System``; continuous TPMs keep float32. Every
downstream value must be identical regardless of the input dtype.
"""

import contextlib
import io

import numpy as np
import pytest

from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.kgeomip import KGeoMIP
from src.controllers.strategies.q_nodes import QNodes
from src.models.base.application import application
from src.models.core.system import NCUBE_DTYPE, System


def test_load_network_returns_uint8_for_deterministic_tpm() -> None:
    """0/1 sample TPMs come back as uint8 with the exact same values."""
    application.set_sample_network_page("A")
    tpm = Manager("1" * 6).load_network()
    assert tpm.dtype == np.uint8
    assert set(np.unique(tpm)) <= {0, 1}


def test_load_network_keeps_float32_for_continuous_tpm() -> None:
    """Continuous TPMs (N15A) must not be truncated to integers."""
    application.set_sample_network_page("A")
    tpm = Manager("1" * 15).load_network()
    assert tpm.dtype == np.float32
    assert ((tpm > 0) & (tpm < 1)).any()


def test_system_cubes_identical_for_uint8_and_float32_input() -> None:
    """Cube tensors are float32 and bit-identical for both input dtypes."""
    rng = np.random.default_rng(3)
    tpm_u8 = rng.integers(0, 2, size=(2**5, 5)).astype(np.uint8)
    state = rng.integers(0, 2, size=5).astype(np.int8)

    sys_u8 = System(tpm_u8, state)
    sys_f32 = System(tpm_u8.astype(np.float32), state)
    for cube_a, cube_b in zip(sys_u8.ncubes, sys_f32.ncubes, strict=True):
        assert cube_a.data.dtype == NCUBE_DTYPE
        assert np.array_equal(cube_a.data, cube_b.data)


@pytest.mark.parametrize("strategy_cls", [GeometricSIA, QNodes])
def test_strategy_loss_identical_for_uint8_and_float32_tpm(strategy_cls) -> None:
    """End-to-end k=2 losses do not depend on the TPM input dtype."""
    application.set_sample_network_page("A")
    state = "1" * 6
    tpm = Manager(state).load_network()
    full = "1" * 6

    with contextlib.redirect_stdout(io.StringIO()):
        loss_u8 = strategy_cls(tpm, state).apply_strategy(full, full, full).loss
        loss_f32 = (
            strategy_cls(tpm.astype(np.float32), state).apply_strategy(full, full, full).loss
        )
    assert loss_u8 == loss_f32


def test_kgeomip_loss_identical_for_uint8_and_float32_tpm() -> None:
    """k-partition losses (cost table included) match for both input dtypes."""
    application.set_sample_network_page("A")
    state = "1" * 6
    tpm = Manager(state).load_network()
    full = "1" * 6

    with contextlib.redirect_stdout(io.StringIO()):
        sols_u8 = KGeoMIP(tpm, state, k=2).apply_strategy_for_ks(full, full, full, (2, 3, 4))
        sols_f32 = KGeoMIP(tpm.astype(np.float32), state, k=2).apply_strategy_for_ks(
            full, full, full, (2, 3, 4)
        )
    for k in (2, 3, 4):
        assert sols_u8[k].loss == sols_f32[k].loss
        assert sols_u8[k].partition == sols_f32[k].partition
