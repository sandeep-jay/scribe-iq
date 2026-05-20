from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.types import EmbeddingResult


@pytest.mark.asyncio
async def test_openai_embedding_provider_maps_vector_and_request():
    settings = Settings(
        embedding_provider="openai",
        openai_api_key="sk-test",
        openai_embeddings_model="text-embedding-3-small",
        openai_embeddings_dimensions=1536,
    )
    fake_resp = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
        model="text-embedding-3-small",
    )
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=fake_resp)

    with patch("app.embeddings.openai_provider.AsyncOpenAI", return_value=mock_client):
        result = await OpenAIEmbeddingProvider(settings).embed_text("hello")

    assert isinstance(result, EmbeddingResult)
    assert result.provider == "openai"
    assert result.model == "text-embedding-3-small"
    assert result.vector == [0.1, 0.2, 0.3]
    assert result.dimensions == 3
    mock_client.embeddings.create.assert_awaited_once()
    call_kwargs = mock_client.embeddings.create.await_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["input"] == ["hello"]
    assert call_kwargs["dimensions"] == 1536
