from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.types import LlmCompletionResult


@pytest.mark.asyncio
async def test_azure_provider_maps_usage_and_model():
    settings = Settings(
        llm_provider="azure_openai",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_chat_deployment="gpt-4o-mini",
    )
    fake_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        model="gpt-4o-mini",
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_resp)
    with patch("app.llm.azure_openai_provider.AsyncAzureOpenAI", return_value=mock_client):
        provider = AzureOpenAIProvider(settings)
        result = await provider.chat_json_complete(
            [{"role": "user", "content": "hi"}], temperature=0.1, max_tokens=100
        )
    assert isinstance(result, LlmCompletionResult)
    assert result.provider == "azure_openai"
    assert result.model == "gpt-4o-mini"
    assert result.prompt_tokens == 11
    assert result.completion_tokens == 7
    mock_client.chat.completions.create.assert_awaited_once()
    call_kwargs = mock_client.chat.completions.create.await_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["response_format"] == {"type": "json_object"}
