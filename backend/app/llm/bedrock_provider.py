"""Amazon Bedrock Converse chat completions."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.config import Settings
from app.llm.bedrock_messages import openai_messages_to_bedrock
from app.llm.errors import LlmConfigurationError, LlmProviderError
from app.llm.types import LlmCompletionResult

_PROVIDER = "bedrock"


class BedrockProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _runtime_client(self) -> Any:
        try:
            import boto3
        except ImportError as exc:
            raise LlmConfigurationError(
                "boto3 is required for LLM_PROVIDER=bedrock; install scribe-iq-backend with boto3."
            ) from exc
        region = (self._settings.aws_region or "").strip()
        if not region:
            raise LlmConfigurationError("AWS_REGION is required for LLM_PROVIDER=bedrock.")
        profile = (self._settings.bedrock_profile_name or "").strip()
        session_kwargs: dict[str, str] = {"region_name": region}
        if profile:
            session_kwargs["profile_name"] = profile
        session = boto3.Session(**session_kwargs)
        return session.client("bedrock-runtime")

    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = 1024,
    ) -> LlmCompletionResult:
        model_id = self._settings.resolved_bedrock_chat_model_id()
        return await self._converse(
            model_id=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            json_mode=False,
        )

    async def chat_json_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LlmCompletionResult:
        model_id = self._settings.resolved_bedrock_json_model_id()
        return await self._converse(
            model_id=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )

    async def _converse(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LlmCompletionResult:
        if not model_id:
            raise LlmConfigurationError("BEDROCK_CHAT_MODEL_ID / BEDROCK_JSON_MODEL_ID is required.")
        system_blocks, bedrock_messages = openai_messages_to_bedrock(messages, json_mode=json_mode)
        if not bedrock_messages:
            raise LlmConfigurationError("Bedrock requires at least one user or assistant message.")

        client = self._runtime_client()
        kwargs: dict[str, Any] = {
            "modelId": model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
        }
        if system_blocks:
            kwargs["system"] = system_blocks

        t0 = time.perf_counter()
        try:
            resp = await asyncio.to_thread(client.converse, **kwargs)
        except Exception as exc:
            raise LlmProviderError(f"Bedrock converse failed: {exc}") from exc

        text = _extract_output_text(resp)
        if not text:
            raise LlmProviderError("Bedrock returned empty content")
        usage = resp.get("usage") or {}
        return LlmCompletionResult(
            text=text.strip(),
            latency_ms=int((time.perf_counter() - t0) * 1000),
            provider=_PROVIDER,
            model=model_id,
            prompt_tokens=int(usage["inputTokens"]) if usage.get("inputTokens") is not None else None,
            completion_tokens=int(usage["outputTokens"]) if usage.get("outputTokens") is not None else None,
        )


def _extract_output_text(resp: dict[str, Any]) -> str:
    output = resp.get("output") or {}
    message = output.get("message") or {}
    parts: list[str] = []
    for block in message.get("content") or []:
        if isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
    return "\n".join(parts)
