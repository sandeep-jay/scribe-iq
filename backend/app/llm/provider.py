"""LLM provider protocol and factory."""

from __future__ import annotations

from typing import Protocol

from app.config import Settings
from app.llm.errors import LlmConfigurationError, LlmJsonModeError, LlmProviderError
from app.llm.types import LlmCompletionResult

__all__ = [
    "LlmConfigurationError",
    "LlmJsonModeError",
    "LlmProvider",
    "LlmProviderError",
    "get_llm_provider",
]


class LlmProvider(Protocol):
    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = 1024,
    ) -> LlmCompletionResult: ...

    async def chat_json_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LlmCompletionResult: ...


def get_llm_provider(settings: Settings) -> LlmProvider:
    provider = settings.normalized_llm_provider()
    match provider:
        case "groq":
            from app.llm.groq_provider import GroqProvider

            return GroqProvider(settings)
        case "azure_openai":
            from app.llm.azure_openai_provider import AzureOpenAIProvider

            return AzureOpenAIProvider(settings)
        case "bedrock":
            from app.llm.bedrock_provider import BedrockProvider

            return BedrockProvider(settings)
        case _:
            raise LlmConfigurationError(f"Unsupported LLM_PROVIDER={settings.llm_provider!r}")
