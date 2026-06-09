"""Tests for the headless analysis runner (:mod:`src.funcs.runner`).

The runner centralizes the strategy registry shared by the web UI and scripts.
These checks exercise sample discovery, the loading helper and that every
registered strategy runs end-to-end on a small network with a finite loss.
"""

import numpy as np
import pytest

from src.constants.base import PATH_SAMPLES
from src.controllers.strategies.exhaustive_k import ExhaustiveK
from src.funcs.runner import (
    STRATEGY_BUILDERS,
    STRATEGY_HELP,
    AnalysisResult,
    available_samples,
    load_tpm,
    run_analysis,
)
from src.models.base.application import application


def test_registry_and_help_cover_the_same_strategies() -> None:
    """Every builder has a one-line help string and vice versa."""
    assert set(STRATEGY_BUILDERS) == set(STRATEGY_HELP)
    assert "KGeoMIP" in STRATEGY_BUILDERS
    assert "KQNodes" in STRATEGY_BUILDERS


def test_available_samples_finds_known_networks() -> None:
    """The shipped samples (N10A, N15A) are discovered."""
    samples = available_samples(PATH_SAMPLES)
    assert "N10A" in samples
    assert "N15A" in samples


def test_load_tpm_shape_matches_nodes() -> None:
    """Loading N4A yields a 2^4 x 4 TPM."""
    tpm = load_tpm("1111", "A")
    assert tpm.shape == (16, 4)


@pytest.mark.parametrize("strategy", list(STRATEGY_BUILDERS))
def test_every_strategy_runs_end_to_end(strategy: str) -> None:
    """Each registered strategy returns a finite, non-negative δ_k on N4A."""
    application.set_sample_network_page("A")
    tpm = load_tpm("1111", "A")
    result = run_analysis(tpm, "1111", strategy, k=3)
    assert isinstance(result, AnalysisResult)
    assert np.isfinite(result.solution.loss)
    assert result.solution.loss >= -1e-12
    assert result.strategy == strategy
    assert result.k == 3


def test_heuristics_do_not_beat_exact() -> None:
    """No registered strategy beats the exact k-MIP ground truth on N4A."""
    application.set_sample_network_page("A")
    tpm = load_tpm("1111", "A")
    exact = run_analysis(tpm, "1111", "ExhaustiveK", k=3)
    assert isinstance(ExhaustiveK(tpm, "1111", k=3), ExhaustiveK)  # registry sanity
    for strategy in STRATEGY_BUILDERS:
        result = run_analysis(tpm, "1111", strategy, k=3)
        assert result.solution.loss >= exact.solution.loss - 1e-9


def test_unknown_strategy_raises() -> None:
    """An unregistered strategy name is rejected."""
    tpm = load_tpm("1111", "A")
    with pytest.raises(KeyError):
        run_analysis(tpm, "1111", "NotAStrategy", k=3)
