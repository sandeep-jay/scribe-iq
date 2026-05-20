"""Amazon Bedrock embedding provider."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.config import Settings
from app.embeddings.errors import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.types import EmbeddingResult

_PROVIDER = "bedrock"


class BedrockEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _runtime_client(self) -> Any:
        from app.aws.bedrock_session import bedrock_runtime_client

        try:
            return bedrock_runtime_client(self._settings)
        except RuntimeError as exc:
            raise EmbeddingConfigurationError(str(exc)) from exc

    async def embed_text(self, text: str) -> EmbeddingResult:
        model_id = self._settings.resolved_aws_bedrock_embedding_model_id()
        if not model_id:
            raise EmbeddingConfigurationError(
                "AWS_BEDROCK_EMBEDDING_MODEL_ID is required for EMBEDDING_PROVIDER=bedrock."
            )
        if not model_id.startswith("amazon.titan-embed-text"):
            raise EmbeddingConfigurationError(
                "Only Amazon Titan text embedding models are supported for Bedrock embeddings. "
                "Use amazon.titan-embed-text-v1 to match EMBED_DIM=1536."
            )

        body: dict[str, object] = {"inputText": text.strip()}
        if model_id.startswith("amazon.titan-embed-text-v2"):
            if self._settings.aws_bedrock_embedding_dimensions is not None:
                body["dimensions"] = self._settings.aws_bedrock_embedding_dimensions
            body["normalize"] = True

        client = self._runtime_client()
        t0 = time.perf_counter()
        try:
            resp = await asyncio.to_thread(
                client.invoke_model,
                modelId=model_id,
                body=json.dumps(body),
                accept="application/json",
                contentType="application/json",
            )
        except Exception as exc:
            raise EmbeddingProviderError(f"Bedrock embedding failed: {exc}") from exc

        payload = _read_json_body(resp)
        embedding = payload.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise EmbeddingProviderError("Bedrock embedding API returned no embedding")
        vec = [float(x) for x in embedding]
        input_tokens = payload.get("inputTextTokenCount")
        return EmbeddingResult(
            vector=vec,
            provider=_PROVIDER,
            model=model_id,
            dimensions=len(vec),
            latency_ms=int((time.perf_counter() - t0) * 1000),
            input_tokens=int(input_tokens) if input_tokens is not None else None,
        )


def _read_json_body(resp: dict[str, Any]) -> dict[str, Any]:
    body = resp.get("body")
    if body is None:
        return resp
    if hasattr(body, "read"):
        raw = body.read()
    else:
        raw = body
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return raw
    raise EmbeddingProviderError("Bedrock embedding API returned an unreadable response body")
