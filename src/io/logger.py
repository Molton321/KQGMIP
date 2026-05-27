import sys
import logging
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Any, Callable

from colorama import init, Fore, Style

from src.constants.base import LOGS_PATH

init(autoreset=True)


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.LIGHTBLACK_EX,
        logging.INFO: Fore.BLUE,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
        logging.FATAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        original = record.levelname
        record.levelname = f"{color}{original}{Style.RESET_ALL}"
        formatted = super().format(record)
        record.levelname = original
        return formatted


class SafeLogger:
    """Logger con soporte de colores, UTF-8 y estructura de directorios por fecha/hora."""

    def __init__(self, name: str):
        self._logger = self._setup(name)

    def _safe_str(self, obj: Any) -> str:
        try:
            return str(obj).encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            return "[Objeto no representable]"

    def _fmt(self, *args, **kwargs) -> str:
        parts = " ".join(self._safe_str(a) for a in args)
        if kwargs:
            parts += " " + " ".join(f"{k}={self._safe_str(v)}" for k, v in kwargs.items())
        return parts

    def _setup(self, name: str) -> logging.Logger:
        base = Path(LOGS_PATH)
        base.mkdir(exist_ok=True)

        now = datetime.now()
        hour_dir = base / now.strftime("%d_%m_%Y") / f"{now.strftime('%H')}hrs"
        hour_dir.mkdir(parents=True, exist_ok=True)

        plain_fmt = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        color_fmt = ColorFormatter(
            "%(levelname)s (%(asctime)s): %(message)s",
            datefmt="%H:%M:%S",
        )

        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        logger.handlers.clear()

        fh = logging.FileHandler(hour_dir / f"{name}.log", mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(plain_fmt)

        lh = logging.FileHandler(base / f"last_{name}.log", mode="w", encoding="utf-8")
        lh.setLevel(logging.DEBUG)
        lh.setFormatter(plain_fmt)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(color_fmt)

        logger.addHandler(fh)
        logger.addHandler(lh)
        logger.addHandler(ch)
        return logger

    def debug(self, *args, **kwargs) -> None:
        self._logger.debug(self._fmt(*args, **kwargs))

    def info(self, *args, **kwargs) -> None:
        self._logger.info(self._fmt(*args, **kwargs))

    def warn(self, *args, **kwargs) -> None:
        self._logger.warning(self._fmt(*args, **kwargs))

    def error(self, *args, **kwargs) -> None:
        self._logger.error(self._fmt(*args, **kwargs))

    def critic(self, *args, **kwargs) -> None:
        self._logger.critical(self._fmt(*args, **kwargs))

    def fatal(self, *args, **kwargs) -> None:
        self._logger.fatal(self._fmt(*args, **kwargs))


def log_execution(logger: SafeLogger):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.debug(f"Iniciando {func.__name__}")
                result = func(*args, **kwargs)
                logger.debug(f"Completado {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Error en {func.__name__}: {e}")
                raise
        return wrapper
    return decorator
