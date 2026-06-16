"""
Central profiling manager and utilities built on pyinstrument.
"""

import warnings
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from pyinstrument import Profiler
from pyinstrument.renderers import HTMLRenderer

from src.constants.base import HTML_EXTENSION, PROFILING_PATH
from src.models.base.application import application


class ProfilingManager:
    """Central profiling manager built on pyinstrument."""

    def __init__(self):
        self.output_dir = Path(PROFILING_PATH)
        self.current_session: str | None = None

    @property
    def enabled(self) -> bool:
        """Whether profiling is currently enabled in the global config."""
        return application.profiler_enabled

    def _setup(self) -> None:
        """Create the output directory when profiling is enabled."""
        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, session_name: str) -> None:
        """Open a timestamped profiling session under session_name."""
        if not self.enabled:
            return
        self._setup()
        timestamp = datetime.now().strftime("%d_%m_%Y/%Hhrs")
        session_path = self.output_dir / session_name / timestamp
        session_path.mkdir(parents=True, exist_ok=True)
        self.current_session = str(session_path.relative_to(self.output_dir))

    def get_output_path(self, name: str) -> Path:
        """Return the HTML path for name within the current session."""
        session_dir = self.current_session or "default"
        return self.output_dir / session_dir / f"{name}.{HTML_EXTENSION}"


class ProfilerContext:
    """Context manager that profiles its body and writes an HTML report."""

    def __init__(self, manager: ProfilingManager, name: str):
        self.manager = manager
        self.name = name
        self.profiler = None

    def __enter__(self):
        """Start the pyinstrument profiler when profiling is enabled."""
        if self.manager.enabled:
            try:
                self.profiler = Profiler(interval=0.001, async_mode="disabled")
                self.profiler.start()
            except ImportError:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.manager.enabled or self.profiler is None:
            return

        self.profiler.stop()
        try:
            html_path = self.manager.get_output_path(self.name)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(
                    self.profiler.output(
                        renderer=HTMLRenderer(show_all=True, timeline=True)
                    )
                )
        except Exception as exc:
            warnings.warn(
                f"Profiling report failed for {self.name}: {exc}", stacklevel=2
            )


profiling_manager = ProfilingManager()


def profile(name: str | None = None, context: dict | None = None) -> Callable:
    """Decorator that profiles functions with pyinstrument."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not profiling_manager.enabled:
                return func(*args, **kwargs)
            profile_name = name or func.__name__
            with ProfilerContext(profiling_manager, profile_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
