"""Shared LLM completion types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LlmCompletionResult:
    text: str
    latency_ms: int
    provider: str
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None


GroqCompletionResult = LlmCompletionResult
