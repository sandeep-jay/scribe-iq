"""Azure OpenAI chat completions."""

from __future__ import annotations

import time

from openai import AsyncAzureOpenAI

from app.config import Settings
from app.llm.errors import LlmConfigurationError, LlmProviderError
from app.llm.types import LlmCompletionResult

_PROVIDER = "azure_openai"


class AzureOpenAIProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> AsyncAzureOpenAI:
        endpoint = (self._settings.azure_openai_endpoint or "").strip()
        key = (self._settings.azure_openai_api_key or "").strip()
        if not endpoint or not key:
            raise LlmConfigurationError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are required for LLM_PROVIDER=azure_openai."
            )
        return AsyncAzureOpenAI(
            api_key=key,
            azure_endpoint=endpoint,
            api_version=self._settings.azure_openai_api_version or "2024-10-21",
        )

    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = 1024,
    ) -> LlmCompletionResult:
        deployment = self._settings.resolved_azure_chat_deployment()
        client = self._client()
        t0 = time.perf_counter()
        try:
            resp = await client.chat.completions.create(
                model=deployment,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise LlmProviderError(f"Azure OpenAI chat completion failed: {exc}") from exc
        return _map_response(resp, deployment, t0, empty_msg="LLM returned empty content")

    async def chat_json_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LlmCompletionResult:
        deployment = self._settings.resolved_azure_json_deployment()
        client = self._client()
        t0 = time.perf_counter()
        try:
            resp = await client.chat.completions.create(
                model=deployment,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LlmProviderError(f"Azure OpenAI JSON completion failed: {exc}") from exc
        return _map_response(resp, deployment, t0, empty_msg="LLM returned empty JSON content")


def _map_response(resp, deployment: str, t0: float, *, empty_msg: str) -> LlmCompletionResult:
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
        model=getattr(resp, "model", None) or deployment,
        prompt_tokens=int(pt) if pt is not None else None,
        completion_tokens=int(ct) if ct is not None else None,
    )
