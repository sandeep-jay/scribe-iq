from __future__ import annotations

import json
import sys
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.embeddings.bedrock_provider import BedrockEmbeddingProvider
from app.embeddings.errors import EmbeddingConfigurationError
from app.embeddings.types import EmbeddingResult


@pytest.mark.asyncio
async def test_bedrock_embedding_provider_maps_titan_response():
    settings = Settings(
        embedding_provider="bedrock",
        aws_region="us-west-2",
        aws_bedrock_embedding_model_id="amazon.titan-embed-text-v1",
    )
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = {
        "body": BytesIO(json.dumps({"embedding": [0.1, 0.2, 0.3], "inputTextTokenCount": 4}).encode())
    }
    mock_boto3 = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = fake_client
    mock_boto3.Session.return_value = mock_session

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        result = await BedrockEmbeddingProvider(settings).embed_text("hello")

    assert isinstance(result, EmbeddingResult)
    assert result.provider == "bedrock"
    assert result.model == "amazon.titan-embed-text-v1"
    assert result.vector == [0.1, 0.2, 0.3]
    assert result.input_tokens == 4
    fake_client.invoke_model.assert_called_once()
    call_kwargs = fake_client.invoke_model.call_args.kwargs
    assert call_kwargs["modelId"] == "amazon.titan-embed-text-v1"
    assert json.loads(call_kwargs["body"]) == {"inputText": "hello"}


@pytest.mark.asyncio
async def test_bedrock_embedding_provider_rejects_unsupported_model():
    settings = Settings(
        embedding_provider="bedrock",
        aws_region="us-west-2",
        aws_bedrock_embedding_model_id="cohere.embed-english-v3",
    )
    provider = BedrockEmbeddingProvider(settings)
    with pytest.raises(EmbeddingConfigurationError, match="Only Amazon Titan"):
        await provider.embed_text("hello")


@pytest.mark.asyncio
async def test_bedrock_titan_v2_includes_dimensions_when_configured():
    settings = Settings(
        embedding_provider="bedrock",
        aws_region="us-west-2",
        aws_bedrock_embedding_model_id="amazon.titan-embed-text-v2:0",
        aws_bedrock_embedding_dimensions=1024,
    )
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = {"body": BytesIO(json.dumps({"embedding": [0.1]}).encode())}
    mock_boto3 = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = fake_client
    mock_boto3.Session.return_value = mock_session

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        await BedrockEmbeddingProvider(settings).embed_text("hello")

    body = json.loads(fake_client.invoke_model.call_args.kwargs["body"])
    assert body == {"inputText": "hello", "dimensions": 1024, "normalize": True}
