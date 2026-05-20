"""OpenAI embedding provider."""

from __future__ import annotations

import time

from openai import AsyncOpenAI

from app.config import Settings
from app.embeddings.errors import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.types import EmbeddingResult

_PROVIDER = "openai"


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> AsyncOpenAI:
        key = (self._settings.openai_api_key or "").strip()
        if not key:
            raise EmbeddingConfigurationError(
                "OPENAI_API_KEY is required for EMBEDDING_PROVIDER=openai."
            )
        return AsyncOpenAI(api_key=key)

    async def embed_text(self, text: str) -> EmbeddingResult:
        model = (self._settings.openai_embeddings_model or "").strip()
        if not model:
            raise EmbeddingConfigurationError(
                "OPENAI_EMBEDDINGS_MODEL is required for EMBEDDING_PROVIDER=openai."
            )
        client = self._client()
        kwargs: dict[str, object] = {"model": model, "input": [text.strip()]}
        if self._settings.openai_embeddings_dimensions is not None:
            kwargs["dimensions"] = self._settings.openai_embeddings_dimensions

        t0 = time.perf_counter()
        try:
            resp = await client.embeddings.create(**kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            raise EmbeddingProviderError(f"OpenAI embedding failed: {exc}") from exc
        if not resp.data:
            raise EmbeddingProviderError("OpenAI embedding API returned no data")

        vec = list(resp.data[0].embedding)
        return EmbeddingResult(
            vector=vec,
            provider=_PROVIDER,
            model=getattr(resp, "model", None) or model,
            dimensions=len(vec),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
