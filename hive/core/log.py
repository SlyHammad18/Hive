import logging
from pathlib import Path

import platformdirs


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


def get_logger(name: str) -> logging.Logger:
    return _logger.getChild(name)
