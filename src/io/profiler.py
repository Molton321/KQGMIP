from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from src.constants.base import HTML_EXTENSION, PROFILING_PATH
from src.base.application import aplicacion


class ProfilingManager:
    """Gestor central de profiling con pyinstrument."""

    def __init__(self):
        self.output_dir = Path(PROFILING_PATH)
        self.current_session: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return aplicacion.profiler_habilitado

    def _setup(self) -> None:
        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, session_name: str) -> None:
        if not self.enabled:
            return
        self._setup()
        timestamp = datetime.now().strftime("%d_%m_%Y/%Hhrs")
        session_path = self.output_dir / session_name / timestamp
        session_path.mkdir(parents=True, exist_ok=True)
        self.current_session = str(session_path.relative_to(self.output_dir))

    def get_output_path(self, name: str) -> Path:
        session_dir = self.current_session or "default"
        return self.output_dir / session_dir / f"{name}.{HTML_EXTENSION}"


class ProfilerContext:
    def __init__(self, manager: ProfilingManager, name: str):
        self.manager = manager
        self.name = name
        self.profiler = None

    def __enter__(self):
        if self.manager.enabled:
            try:
                from pyinstrument import Profiler
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
            from pyinstrument.renderers import HTMLRenderer
            html_path = self.manager.get_output_path(self.name)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.profiler.output(renderer=HTMLRenderer(show_all=True, timeline=True)))
        except Exception:
            pass


gestor_perfilado = ProfilingManager()


def profile(name: Optional[str] = None, context: Optional[dict] = None) -> Callable:
    """Decorador para perfilar funciones con pyinstrument."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not gestor_perfilado.enabled:
                return func(*args, **kwargs)
            profile_name = name or func.__name__
            with ProfilerContext(gestor_perfilado, profile_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
