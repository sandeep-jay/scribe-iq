"""Shared embedding result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vector: list[float]
    provider: str
    model: str | None
    dimensions: int
    latency_ms: int | None = None
    input_tokens: int | None = None
