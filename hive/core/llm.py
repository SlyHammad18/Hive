from collections.abc import AsyncIterator

import litellm
from litellm import AuthenticationError, RateLimitError, Timeout

from hive.core.config import load_config

PROVIDER_MODELS: dict[str, list[str]] = {
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


def list_available_models(config: dict | None = None) -> list[str]:
    if config is None:
        config = load_config()
    providers = config.get("providers", {})
    models: list[str] = []
    for key in providers:
        value = providers[key]
        if not value:
            continue
        if key == "ollama_base_url":
            models.extend(PROVIDER_MODELS.get(key, []))
            continue
        if key in PROVIDER_MODELS:
            models.extend(PROVIDER_MODELS[key])
    return models


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
        return content, token_counts
    except AuthenticationError:
        raise
    except RateLimitError:
        raise
    except Timeout:
        raise
