from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.embeddings.azure_openai_provider import AzureOpenAIEmbeddingProvider
from app.embeddings.errors import EmbeddingConfigurationError
from app.embeddings.types import EmbeddingResult


@pytest.mark.asyncio
async def test_azure_embedding_provider_maps_vector_and_request():
    settings = Settings(
        embedding_provider="azure_openai",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_api_version="2024-02-01",
        azure_embedding_deployment="text-embedding-3-small",
        azure_embeddings_dimensions=1536,
    )
    fake_resp = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2])],
        model="text-embedding-3-small",
    )
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=fake_resp)

    with patch("app.embeddings.azure_openai_provider.AsyncAzureOpenAI", return_value=mock_client):
        result = await AzureOpenAIEmbeddingProvider(settings).embed_text("hello")

    assert isinstance(result, EmbeddingResult)
    assert result.provider == "azure_openai"
    assert result.model == "text-embedding-3-small"
    assert result.vector == [0.1, 0.2]
    mock_client.embeddings.create.assert_awaited_once()
    call_kwargs = mock_client.embeddings.create.await_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["input"] == ["hello"]
    assert call_kwargs["dimensions"] == 1536


@pytest.mark.asyncio
async def test_azure_embedding_provider_requires_deployment():
    settings = Settings(
        embedding_provider="azure_openai",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_embedding_deployment=None,
    )
    provider = AzureOpenAIEmbeddingProvider(settings)
    with pytest.raises(EmbeddingConfigurationError, match="AZURE_EMBEDDING_DEPLOYMENT"):
        await provider.embed_text("hello")
