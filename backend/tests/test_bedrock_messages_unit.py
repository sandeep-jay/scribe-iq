from __future__ import annotations

import pytest

from app.llm.bedrock_messages import openai_messages_to_bedrock
from app.llm.errors import LlmConfigurationError


def test_separates_system_and_maps_user_content():
    system, messages = openai_messages_to_bedrock(
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
    )
    assert system == [{"text": "You are helpful."}]
    assert messages == [{"role": "user", "content": [{"text": "Hello"}]}]


def test_merges_multiple_system_messages():
    system, messages = openai_messages_to_bedrock(
        [
            {"role": "system", "content": "A"},
            {"role": "system", "content": "B"},
            {"role": "user", "content": "Hi"},
        ]
    )
    assert system == [{"text": "A"}, {"text": "B"}]
    assert len(messages) == 1


def test_json_mode_appends_enforcement_to_system():
    system, _ = openai_messages_to_bedrock(
        [{"role": "system", "content": "Base"}], json_mode=True
    )
    assert any("JSON object" in block["text"] for block in system)


def test_unsupported_role_raises():
    with pytest.raises(LlmConfigurationError, match="Unsupported message role"):
        openai_messages_to_bedrock([{"role": "tool", "content": "x"}])
