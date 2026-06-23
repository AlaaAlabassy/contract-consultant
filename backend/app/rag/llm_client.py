"""Thin wrapper around OpenRouter's OpenAI-compatible chat completions endpoint.

No official SDK is used (httpx is already a dependency) - this is a single
REST call, not worth pulling in another client library for.
"""

from __future__ import annotations

import httpx

from app.config import settings


def chat_completion(messages: list[dict], model: str | None = None, temperature: float = 0.0) -> str:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    response = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        json={
            "model": model or settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
