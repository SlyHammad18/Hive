import os
import tomllib
from pathlib import Path

import tomli_w
from platformdirs import PlatformDirs

APP_NAME = "hive"
CONFIG_FILENAME = "config.toml"

_dirs = PlatformDirs(APP_NAME, APP_NAME)
CONFIG_PATH = _dirs.user_config_path / CONFIG_FILENAME


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("rb") as f:
        return dict(tomllib.load(f))


def save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("wb") as f:
        tomli_w.dump(data, f)


def apply_config(config: dict) -> None:
    providers = config.get("providers", {})
    for key, value in providers.items():
        env_key = key.upper()
        if value:
            os.environ[env_key] = value

    search = config.get("search", {})
    tavily_key = search.get("tavily_api_key", "")
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "•" * len(key)
    prefix = key[:7]
    suffix = key[-4:]
    masked_len = len(key) - 11
    return f"{prefix}{'•' * masked_len}{suffix}"
