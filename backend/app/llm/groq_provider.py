"""Groq chat completions (OpenAI-compatible API)."""

from __future__ import annotations

import time

from openai import AsyncOpenAI

from app.config import Settings
from app.llm.errors import LlmConfigurationError, LlmProviderError
from app.llm.types import LlmCompletionResult

_PROVIDER = "groq"


class GroqProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> AsyncOpenAI:
        key = (self._settings.groq_api_key or "").strip()
        if not key:
            raise LlmConfigurationError(
                "GROQ_API_KEY is not set; configure Groq credentials for LLM_PROVIDER=groq."
            )
        return AsyncOpenAI(api_key=key, base_url=self._settings.groq_base_url)

    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = 1024,
    ) -> LlmCompletionResult:
        client = self._client()
        t0 = time.perf_counter()
        try:
            resp = await client.chat.completions.create(
                model=self._settings.groq_chat_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise LlmProviderError(f"Groq chat completion failed: {exc}") from exc
        return _map_response(resp, self._settings.groq_chat_model, t0, empty_msg="LLM returned empty content")

    async def chat_json_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LlmCompletionResult:
        client = self._client()
        t0 = time.perf_counter()
        try:
            resp = await client.chat.completions.create(
                model=self._settings.groq_chat_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LlmProviderError(f"Groq JSON completion failed: {exc}") from exc
        return _map_response(
            resp, self._settings.groq_chat_model, t0, empty_msg="LLM returned empty JSON content"
        )


def _map_response(resp, fallback_model: str, t0: float, *, empty_msg: str) -> LlmCompletionResult:
    latency_ms = int((time.perf_counter() - t0) * 1000)
    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        raise LlmProviderError(empty_msg)
    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", None) if usage else None
    ct = getattr(usage, "completion_tokens", None) if usage else None
    return LlmCompletionResult(
        text=content.strip(),
        latency_ms=latency_ms,
        provider=_PROVIDER,
        model=getattr(resp, "model", None) or fallback_model,
        prompt_tokens=int(pt) if pt is not None else None,
        completion_tokens=int(ct) if ct is not None else None,
    )
