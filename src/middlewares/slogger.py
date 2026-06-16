"""
A logging utility that provides colorized console output, UTF-8 safety, and organized file logging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from colorama import Fore, Style, init

from src.constants.base import LOGS_PATH

init(autoreset=True)


class ColorFormatter(logging.Formatter):
    """Logging formatter that colorizes the level name per severity."""

    COLORS = {
        logging.DEBUG: Fore.LIGHTBLACK_EX,
        logging.INFO: Fore.BLUE,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
        logging.FATAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the record, wrapping its level name in the matching color."""
        color = self.COLORS.get(record.levelno, "")
        original = record.levelname
        record.levelname = f"{color}{original}{Style.RESET_ALL}"
        formatted = super().format(record)
        record.levelname = original
        return formatted


class SafeLogger:
    """Logger with color support, UTF-8, and a date/hour directory structure.
    Instances are cached by name so that repeated construction with the same
    tag returns the existing logger (avoiding duplicate handlers).
    """

    _instances: dict[str, SafeLogger] = {}
    _logger: logging.Logger
    _initialized: bool

    def __new__(cls, name: str) -> SafeLogger:
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._logger = instance._setup(name)
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

    def _safe_str(self, obj: Any) -> str:
        """Stringify any object, never raising on undecodable content."""
        try:
            return str(obj).encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            return "[Objeto no representable]"

    def _fmt(self, *args, **kwargs) -> str:
        """Join positional args and (key=value) kwargs into one safe message."""
        parts = " ".join(self._safe_str(a) for a in args)
        if kwargs:
            parts += " " + " ".join(
                f"{k}={self._safe_str(v)}" for k, v in kwargs.items()
            )
        return parts

    def _setup(self, name: str) -> logging.Logger:
        """Set up a logger with file and console handlers, color support, and UTF-8 encoding."""
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
        logger.setLevel(logging.DEBUG)
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
        """Emit a DEBUG record from the safely-formatted arguments."""
        self._logger.debug(self._fmt(*args, **kwargs))

    def info(self, *args, **kwargs) -> None:
        """Emit an INFO record from the safely-formatted arguments."""
        self._logger.info(self._fmt(*args, **kwargs))

    def warn(self, *args, **kwargs) -> None:
        """Emit a WARNING record from the safely-formatted arguments."""
        self._logger.warning(self._fmt(*args, **kwargs))

    def error(self, *args, **kwargs) -> None:
        """Emit an ERROR record from the safely-formatted arguments."""
        self._logger.error(self._fmt(*args, **kwargs))

    def critic(self, *args, **kwargs) -> None:
        """Emit a CRITICAL record from the safely-formatted arguments."""
        self._logger.critical(self._fmt(*args, **kwargs))

    def fatal(self, *args, **kwargs) -> None:
        """Emit a FATAL record from the safely-formatted arguments."""
        self._logger.fatal(self._fmt(*args, **kwargs))
