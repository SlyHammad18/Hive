import pytest

from hive.core import llm


def test_list_available_models_empty() -> None:
    assert llm.list_available_models({}) == []


def test_list_available_models_with_keys() -> None:
    config = {"providers": {"anthropic_api_key": "sk-ant-test", "openai_api_key": "sk-test"}}
    models = llm.list_available_models(config)
    assert "claude-sonnet-4-6" in models
    assert "gpt-4o" in models


def test_list_available_models_includes_groq() -> None:
    config = {"providers": {"groq_api_key": "gsk-test"}}
    models = llm.list_available_models(config)
    assert "groq/llama-3.1-70b-versatile" in models
    assert "groq/mixtral-8x7b-32768" in models


def test_list_available_models_ignores_empty_keys() -> None:
    config = {"providers": {"openai_api_key": "", "anthropic_api_key": None}}
    models = llm.list_available_models(config)
    assert models == []


def test_list_available_models_includes_ollama() -> None:
    config = {"providers": {"ollama_base_url": "http://localhost:11434"}}
    models = llm.list_available_models(config)
    assert any("ollama/" in m for m in models)
