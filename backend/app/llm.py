"""LLM completions (Groq OpenAI-compatible API)."""

from __future__ import annotations

import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import get_settings


@dataclass(frozen=True, slots=True)
class GroqCompletionResult:
    """Structured Groq chat completion for auditing (latency + usage when present)."""

    text: str
    latency_ms: int
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None


async def groq_chat_complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
) -> GroqCompletionResult:
    settings = get_settings()
    key = (settings.groq_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set; chat requires Groq credentials for Phase-1 scaffold."
        )
    client = AsyncOpenAI(api_key=key, base_url=settings.groq_base_url)
    t0 = time.perf_counter()
    resp = await client.chat.completions.create(
        model=settings.groq_chat_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        raise RuntimeError("LLM returned empty content")
    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", None) if usage else None
    ct = getattr(usage, "completion_tokens", None) if usage else None
    return GroqCompletionResult(
        text=content.strip(),
        latency_ms=latency_ms,
        model=getattr(resp, "model", None) or settings.groq_chat_model,
        prompt_tokens=int(pt) if pt is not None else None,
        completion_tokens=int(ct) if ct is not None else None,
    )


async def groq_chat_json_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> GroqCompletionResult:
    """Groq Chat Completions in JSON-object mode."""
    settings = get_settings()
    key = (settings.groq_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set; structured note generation requires Groq credentials."
        )
    client = AsyncOpenAI(api_key=key, base_url=settings.groq_base_url)
    t0 = time.perf_counter()
    resp = await client.chat.completions.create(
        model=settings.groq_chat_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        raise RuntimeError("LLM returned empty JSON content")
    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", None) if usage else None
    ct = getattr(usage, "completion_tokens", None) if usage else None
    return GroqCompletionResult(
        text=content.strip(),
        latency_ms=latency_ms,
        model=getattr(resp, "model", None) or settings.groq_chat_model,
        prompt_tokens=int(pt) if pt is not None else None,
        completion_tokens=int(ct) if ct is not None else None,
    )
