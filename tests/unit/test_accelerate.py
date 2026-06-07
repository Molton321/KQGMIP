"""Correctness of the optional Numba acceleration (Phase 6).

The result must be identical whether the Numba backend or the NumPy fallback is
active, so the test is backend-agnostic and pins the kernel against an explicit
reference.
"""

import numpy as np

from src.funcs import accelerate


def test_backend_is_known() -> None:
    assert accelerate.BACKEND in {"numba", "numpy"}


def test_batch_effect_emd_matches_reference() -> None:
    rng = np.random.default_rng(0)
    baseline = rng.random(7).astype(np.float32)
    distributions = rng.random((32, 7)).astype(np.float32)

    result = accelerate.batch_effect_emd(distributions, baseline)
    reference = np.abs(distributions - baseline).sum(axis=1).astype(np.float32)

    assert result.shape == (32,)
    assert np.allclose(result, reference, atol=1e-5)


def test_batch_effect_emd_matches_scalar_effect_emd() -> None:
    """Each row's batch result equals the per-row scalar effect_emd."""
    from src.funcs.emd import effect_emd

    baseline = np.array([0.1, 0.9, 0.5, 0.0], dtype=np.float32)
    distributions = np.array(
        [[0.2, 0.8, 0.5, 0.1], [0.1, 0.9, 0.5, 0.0]], dtype=np.float32
    )
    batched = accelerate.batch_effect_emd(distributions, baseline)
    for i in range(distributions.shape[0]):
        assert batched[i] == np.float32(
            effect_emd(distributions[i], baseline)
        ) or np.isclose(batched[i], effect_emd(distributions[i], baseline), atol=1e-5)
