import pytest

from src.models.base.application import application


@pytest.fixture(autouse=True)
def _disable_profiling():
    previous = application.profiler_enabled
    application.disable_profiling()
    yield
    application.profiler_enabled = previous
