from __future__ import annotations

import pytest

from app.config import Settings
from app.llm import get_llm_provider
from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.bedrock_provider import BedrockProvider
from app.llm.errors import LlmConfigurationError
from app.llm.groq_provider import GroqProvider


def test_factory_selects_groq():
    settings = Settings(llm_provider="groq")
    assert isinstance(get_llm_provider(settings), GroqProvider)


def test_factory_selects_azure_openai():
    settings = Settings(llm_provider="azure_openai")
    assert isinstance(get_llm_provider(settings), AzureOpenAIProvider)


def test_factory_selects_azure_alias():
    settings = Settings(llm_provider="azure")
    assert isinstance(get_llm_provider(settings), AzureOpenAIProvider)


def test_factory_selects_bedrock():
    settings = Settings(llm_provider="bedrock")
    assert isinstance(get_llm_provider(settings), BedrockProvider)


def test_unsupported_provider_raises_configuration_error():
    settings = Settings(llm_provider="unknown_vendor")
    with pytest.raises(LlmConfigurationError, match="Unsupported LLM_PROVIDER"):
        get_llm_provider(settings)


def test_groq_missing_key_raises_configuration_error():
    settings = Settings(llm_provider="groq", groq_api_key=None)
    provider = get_llm_provider(settings)
    with pytest.raises(LlmConfigurationError, match="GROQ_API_KEY"):
        provider._client()


def test_azure_deployment_aliases():
    settings = Settings(
        llm_provider="azure",
        azure_openai_chat_deployment="",
        azure_openai_json_deployment="",
        azure_openai_deployment="legacy-chat",
        azure_openai_mini_deployment="legacy-mini",
    )
    assert settings.resolved_azure_chat_deployment() == "legacy-chat"
    assert settings.resolved_azure_json_deployment() == "legacy-chat"


def test_llm_json_mode_capability():
    assert Settings(llm_provider="groq").llm_json_mode_capability() == "native"
    assert Settings(llm_provider="azure_openai").llm_json_mode_capability() == "native"
    assert Settings(llm_provider="bedrock").llm_json_mode_capability() == "prompt_enforced"
