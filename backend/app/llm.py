"""LLM completions (Groq OpenAI-compatible API)."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.config import get_settings


async def groq_chat_complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
) -> str:
    settings = get_settings()
    key = (settings.groq_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set; chat requires Groq credentials for Phase-1 scaffold."
        )
    client = AsyncOpenAI(api_key=key, base_url=settings.groq_base_url)
    resp = await client.chat.completions.create(
        model=settings.groq_chat_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
    )
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        raise RuntimeError("LLM returned empty content")
    return content.strip()


async def groq_chat_json_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """Groq Chat Completions in JSON-object mode."""
    settings = get_settings()
    key = (settings.groq_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set; structured note generation requires Groq credentials."
        )
    client = AsyncOpenAI(api_key=key, base_url=settings.groq_base_url)
    resp = await client.chat.completions.create(
        model=settings.groq_chat_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        raise RuntimeError("LLM returned empty JSON content")
    return content.strip()
