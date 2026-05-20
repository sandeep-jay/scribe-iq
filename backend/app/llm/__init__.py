"""Provider-agnostic LLM completions."""

from __future__ import annotations

from app.config import get_settings
from app.llm.errors import LlmConfigurationError, LlmJsonModeError, LlmProviderError
from app.llm.provider import get_llm_provider
from app.llm.types import GroqCompletionResult, LlmCompletionResult

__all__ = [
    "GroqCompletionResult",
    "LlmCompletionResult",
    "LlmConfigurationError",
    "LlmJsonModeError",
    "LlmProviderError",
    "chat_complete",
    "chat_json_completion",
    "get_llm_provider",
    "groq_chat_complete",
    "groq_chat_json_completion",
]


async def chat_complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = 1024,
) -> LlmCompletionResult:
    settings = get_settings()
    provider = get_llm_provider(settings)
    return await provider.chat_complete(
        messages, temperature=temperature, max_tokens=max_tokens
    )


async def chat_json_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> LlmCompletionResult:
    settings = get_settings()
    provider = get_llm_provider(settings)
    return await provider.chat_json_complete(
        messages, temperature=temperature, max_tokens=max_tokens
    )


# Backward-compatible aliases (deprecated; use chat_complete / chat_json_completion).
groq_chat_complete = chat_complete
groq_chat_json_completion = chat_json_completion
