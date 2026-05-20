"""Azure OpenAI embedding provider."""

from __future__ import annotations

import time

from openai import AsyncAzureOpenAI

from app.config import Settings
from app.embeddings.errors import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.types import EmbeddingResult

_PROVIDER = "azure_openai"


class AzureOpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> AsyncAzureOpenAI:
        endpoint = (self._settings.azure_openai_endpoint or "").strip()
        key = (self._settings.azure_openai_api_key or "").strip()
        if not endpoint or not key:
            raise EmbeddingConfigurationError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are required "
                "for EMBEDDING_PROVIDER=azure_openai."
            )
        return AsyncAzureOpenAI(
            api_key=key,
            azure_endpoint=endpoint,
            api_version=self._settings.azure_openai_api_version or "2024-10-21",
        )

    async def embed_text(self, text: str) -> EmbeddingResult:
        deployment = (self._settings.azure_embedding_deployment or "").strip()
        if not deployment:
            raise EmbeddingConfigurationError(
                "AZURE_EMBEDDING_DEPLOYMENT is required for EMBEDDING_PROVIDER=azure_openai."
            )
        client = self._client()
        kwargs: dict[str, object] = {"model": deployment, "input": [text.strip()]}
        if self._settings.azure_embeddings_dimensions is not None:
            kwargs["dimensions"] = self._settings.azure_embeddings_dimensions

        t0 = time.perf_counter()
        try:
            resp = await client.embeddings.create(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise EmbeddingProviderError(f"Azure OpenAI embedding failed: {exc}") from exc
        if not resp.data:
            raise EmbeddingProviderError("Azure OpenAI embedding API returned no data")

        vec = list(resp.data[0].embedding)
        return EmbeddingResult(
            vector=vec,
            provider=_PROVIDER,
            model=getattr(resp, "model", None) or deployment,
            dimensions=len(vec),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
