import os
import tomllib
from pathlib import Path

import tomli_w
from platformdirs import PlatformDirs

from hive.core.log import get_logger

APP_NAME = "hive"
CONFIG_FILENAME = "config.toml"

_dirs = PlatformDirs(APP_NAME, APP_NAME)
CONFIG_PATH = _dirs.user_config_path / CONFIG_FILENAME

_log = get_logger("config")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        _log.debug("config file not found at %s", CONFIG_PATH)
        return {}
    with CONFIG_PATH.open("rb") as f:
        data = dict(tomllib.load(f))
    _log.debug("loaded config from %s: %s", CONFIG_PATH, {k: ("***" if "key" in k else v) for k, v in data.get("providers", {}).items()})
    return data


def save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("wb") as f:
        tomli_w.dump(data, f)
    _log.debug("saved config to %s: %s", CONFIG_PATH, {k: ("***" if "key" in k else v) for k, v in data.get("providers", {}).items()})


def apply_config(config: dict) -> None:
    providers = config.get("providers", {})
    for key, value in providers.items():
        env_key = key.upper()
        if value:
            os.environ[env_key] = value
            _log.debug("set env %s = ***", env_key)

    search = config.get("search", {})
    tavily_key = search.get("tavily_api_key", "")
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key
        _log.debug("set env TAVILY_API_KEY = ***")


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "•" * len(key)
    prefix = key[:7]
    suffix = key[-4:]
    masked_len = len(key) - 11
    return f"{prefix}{'•' * masked_len}{suffix}"
