from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.llm.bedrock_provider import BedrockProvider
from app.llm.types import LlmCompletionResult


@pytest.mark.asyncio
async def test_bedrock_provider_maps_converse_response():
    settings = Settings(
        llm_provider="bedrock",
        aws_region="us-west-2",
        aws_bedrock_chat_model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    )
    fake_client = MagicMock()
    fake_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "hello"}]}},
        "usage": {"inputTokens": 3, "outputTokens": 5},
    }
    mock_boto3 = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = fake_client
    mock_boto3.Session.return_value = mock_session

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        provider = BedrockProvider(settings)
        result = await provider.chat_complete(
            [{"role": "user", "content": "Hi"}], temperature=0.2, max_tokens=50
        )
    assert isinstance(result, LlmCompletionResult)
    assert result.provider == "bedrock"
    assert result.text == "hello"
    assert result.prompt_tokens == 3
    assert result.completion_tokens == 5
