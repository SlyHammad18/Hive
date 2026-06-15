import logging
import os
import sys
from pathlib import Path

import platformdirs


_console_level: int = logging.DEBUG if os.environ.get("HIVE_LOG_VERBOSE") else logging.INFO


_console_handler: logging.Handler | None = None
if os.environ.get("HIVE_CONSOLE_LOG"):
    _console_handler = logging.StreamHandler(sys.stderr)
    _console_handler.setLevel(_console_level)
    _console_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    _console_handler.setFormatter(_console_fmt)


_log_dir = Path(platformdirs.user_log_dir("hive", ensure_exists=True))
_log_path = _log_dir / "hive.log"

_logger = logging.getLogger("hive")
_logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(str(_log_path), mode="a", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_fh.setFormatter(_fmt)
_logger.handlers.clear()
_logger.addHandler(_fh)

if _console_handler is not None:
    _logger.addHandler(_console_handler)


def get_logger(name: str) -> logging.Logger:
    return _logger.getChild(name)
