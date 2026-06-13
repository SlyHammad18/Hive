import asyncio
from collections.abc import AsyncIterator
from time import monotonic

import httpx
import litellm
from litellm import AuthenticationError, RateLimitError, Timeout

from hive.core.config import load_config
from hive.core.log import get_logger

_log = get_logger("llm")

_FALLBACK_MODELS: dict[str, list[str]] = {
    "openai_api_key": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "anthropic_api_key": [
        "claude-sonnet-4-6",
        "claude-3-5-sonnet-latest",
        "claude-3-haiku",
    ],
    "google_api_key": [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-2.0-flash-exp",
    ],
    "groq_api_key": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "groq/llama-3.1-8b-instant",
        "groq/mixtral-8x7b-32768",
        "groq/gemma2-9b-it",
    ],
    "ollama_base_url": ["ollama/llama3.2", "ollama/mistral"],
}

_cache: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL = 300

_TIMEOUT = httpx.Timeout(5.0)


async def _fetch_openai_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        models = [m["id"] for m in data.get("data", []) if m["id"].startswith("gpt-")]
        return sorted(models)


async def _fetch_groq_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        models = ["groq/" + m["id"] for m in data.get("data", [])]
        return sorted(models)


async def _fetch_google_models(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        models = [
            "gemini/" + m["name"].removeprefix("models/")
            for m in data.get("models", [])
            if "gemini" in m["name"]
        ]
        return sorted(models)


async def _fetch_ollama_models(base_url: str) -> list[str]:
    url = base_url.rstrip("/") + "/api/tags"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return sorted(models)


_FETCHERS: dict[str, callable] = {
    "openai_api_key": _fetch_openai_models,
    "groq_api_key": _fetch_groq_models,
    "google_api_key": _fetch_google_models,
    "ollama_base_url": _fetch_ollama_models,
}


async def fetch_provider_models(provider_key: str, value: str) -> list[str]:
    _log.debug("fetch_provider_models: key=%s", provider_key)
    now = monotonic()
    cache_key = provider_key + ":" + value
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        _log.debug("  cache HIT for %s (%d models)", cache_key, len(cached[1]))
        return cached[1]

    fetcher = _FETCHERS.get(provider_key)
    if not fetcher:
        _log.debug("  no fetcher for %s, using fallback", provider_key)
        fallback = _FALLBACK_MODELS.get(provider_key, [])
        _cache[cache_key] = (now, fallback)
        return fallback

    try:
        models = await fetcher(value)
        _log.debug("  fetched %d models from API for %s", len(models), provider_key)
        _cache[cache_key] = (now, models)
        return models
    except Exception as e:
        _log.debug("  fetch failed for %s: %s, using fallback", provider_key, e)
        fallback = _FALLBACK_MODELS.get(provider_key, [])
        _cache[cache_key] = (now, fallback)
        return fallback


def list_available_models(config: dict | None = None) -> list[str]:
    if config is None:
        config = load_config()
    providers = config.get("providers", {})
    _log.debug("list_available_models: providers with values: %s", {k for k, v in providers.items() if v})
    models: list[str] = []
    now = monotonic()
    for key in providers:
        value = providers[key]
        if not value:
            continue
        cache_key = key + ":" + value
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL:
            _log.debug("  cache HIT for %s (%d models)", cache_key, len(cached[1]))
            models.extend(cached[1])
        else:
            fallback = _FALLBACK_MODELS.get(key, [])
            _log.debug("  cache MISS for %s, using fallback (%d models)", cache_key, len(fallback))
            models.extend(fallback)
    _log.debug("  total models returned: %d", len(models))
    return models


def clear_model_cache() -> None:
    _cache.clear()


async def stream(
    messages: list[dict],
    model: str,
    **kwargs: object,
) -> AsyncIterator[str]:
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content  # type: ignore[union-attr]
            if content:
                yield content
    except AuthenticationError:
        yield f"Authentication failed for model '{model}'. Check your API key."
    except RateLimitError:
        yield f"Rate limit exceeded for model '{model}'. Try again later."
    except Timeout:
        yield f"Request timed out for model '{model}'."
    except Exception:
        yield f"Unexpected error with model '{model}'."


async def complete(
    messages: list[dict],
    model: str,
    **kwargs: object,
) -> tuple[str, dict[str, int]]:
    _log.debug("complete: model=%s, msgs=%d", model, len(messages))
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            **kwargs,
        )
        content = response.choices[0].message.content or ""  # type: ignore[union-attr]
        usage = getattr(response, "usage", None)
        token_counts: dict[str, int] = {}
        if usage:
            token_counts = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        _log.debug("  complete OK: tokens=%s, content_len=%d", token_counts, len(content))
        return content, token_counts
    except AuthenticationError:
        _log.error("  AuthenticationError for model %s", model)
        raise
    except RateLimitError:
        _log.error("  RateLimitError for model %s", model)
        raise
    except Timeout:
        _log.error("  Timeout for model %s", model)
        raise
