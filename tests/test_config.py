import os
from pathlib import Path

import pytest

from hive.core import config


@pytest.fixture(autouse=True)
def tmp_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    return path


def test_default_load_returns_empty_dict(tmp_config_path: Path) -> None:
    assert config.load_config() == {}


def test_save_and_load_round_trip(tmp_config_path: Path) -> None:
    data = {
        "providers": {
            "anthropic_api_key": "sk-ant-test123",
            "groq_api_key": "gsk_test789",
        },
        "defaults": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    }
    config.save_config(data)
    loaded = config.load_config()
    assert loaded == data


def test_apply_config_sets_env(tmp_config_path: Path) -> None:
    data = {
        "providers": {
            "anthropic_api_key": "sk-ant-test123",
            "groq_api_key": "gsk_test789",
        },
        "search": {"tavily_api_key": "tvly-test456"},
    }
    config.apply_config(data)
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test123"
    assert os.environ.get("GROQ_API_KEY") == "gsk_test789"
    assert os.environ.get("TAVILY_API_KEY") == "tvly-test456"


def test_mask_key_short() -> None:
    assert config.mask_key("") == ""
    assert config.mask_key("ab") == "••"
    assert config.mask_key("12345678") == "••••••••"


def test_mask_key_long() -> None:
    masked = config.mask_key("sk-ant-test12345")
    assert masked == "sk-ant-•••••2345"
    assert "test" not in masked


