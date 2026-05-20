from __future__ import annotations

import pytest

from app.config import Settings
from app.embeddings import vector_literal
from app.embeddings.azure_openai_provider import AzureOpenAIEmbeddingProvider
from app.embeddings.bedrock_provider import BedrockEmbeddingProvider
from app.embeddings.errors import EmbeddingConfigurationError
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.provider import get_embedding_provider
from app.embeddings.types import EmbeddingResult


def test_embedding_factory_selects_openai():
    settings = Settings(embedding_provider="openai")
    assert isinstance(get_embedding_provider(settings), OpenAIEmbeddingProvider)


def test_embedding_factory_selects_azure_openai_and_alias():
    assert isinstance(
        get_embedding_provider(Settings(embedding_provider="azure_openai")),
        AzureOpenAIEmbeddingProvider,
    )
    assert isinstance(
        get_embedding_provider(Settings(embedding_provider="azure")),
        AzureOpenAIEmbeddingProvider,
    )


def test_embedding_factory_selects_bedrock():
    settings = Settings(embedding_provider="bedrock")
    assert isinstance(get_embedding_provider(settings), BedrockEmbeddingProvider)


def test_embedding_factory_rejects_none_and_unknown():
    with pytest.raises(EmbeddingConfigurationError, match="Embeddings unavailable"):
        get_embedding_provider(Settings(embedding_provider="none"))
    with pytest.raises(EmbeddingConfigurationError, match="Unsupported EMBEDDING_PROVIDER"):
        get_embedding_provider(Settings(embedding_provider="other"))


def test_embedding_configured_for_providers():
    assert Settings(embedding_provider="openai", openai_api_key="sk-test").embedding_configured()
    assert Settings(
        embedding_provider="azure_openai",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="key",
        azure_embedding_deployment="text-embedding-3-small",
    ).embedding_configured()
    assert Settings(
        embedding_provider="bedrock",
        aws_region="us-west-2",
        aws_bedrock_embedding_model_id="amazon.titan-embed-text-v1",
    ).embedding_configured()
    assert not Settings(embedding_provider="bedrock", aws_region="us-west-2").embedding_configured()


def test_resolved_embedding_model_and_vector_literal():
    assert Settings(embedding_provider="openai").resolved_embedding_model() == "text-embedding-3-small"
    assert (
        Settings(
            embedding_provider="azure_openai",
            azure_embedding_deployment="embed-small",
        ).resolved_embedding_model()
        == "embed-small"
    )
    assert (
        Settings(
            embedding_provider="bedrock",
            aws_bedrock_embedding_model_id="amazon.titan-embed-text-v1",
        ).resolved_embedding_model()
        == "amazon.titan-embed-text-v1"
    )
    assert vector_literal([1, 2.5]) == "[1.00000000,2.50000000]"


def test_embedding_result_shape():
    result = EmbeddingResult(vector=[0.1, 0.2], provider="openai", model="m", dimensions=2)
    assert result.dimensions == 2
