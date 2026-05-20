"""Embedding provider protocol and factory."""

from __future__ import annotations

from typing import Protocol

from app.config import Settings
from app.embeddings.errors import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.types import EmbeddingResult

__all__ = [
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "get_embedding_provider",
]


class EmbeddingProvider(Protocol):
    async def embed_text(self, text: str) -> EmbeddingResult: ...


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.normalized_embedding_provider()
    match provider:
        case "openai":
            from app.embeddings.openai_provider import OpenAIEmbeddingProvider

            return OpenAIEmbeddingProvider(settings)
        case "azure_openai":
            from app.embeddings.azure_openai_provider import AzureOpenAIEmbeddingProvider

            return AzureOpenAIEmbeddingProvider(settings)
        case "bedrock":
            from app.embeddings.bedrock_provider import BedrockEmbeddingProvider

            return BedrockEmbeddingProvider(settings)
        case "none":
            raise EmbeddingConfigurationError(
                "Embeddings unavailable: set EMBEDDING_PROVIDER to openai, azure_openai, or bedrock, "
                "then run scribe-load-corpus --embed."
            )
        case _:
            raise EmbeddingConfigurationError(
                f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}"
            )
