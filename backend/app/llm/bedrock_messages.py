"""Convert OpenAI-style chat messages to Bedrock Converse format."""

from __future__ import annotations

from app.llm.errors import LlmConfigurationError

_JSON_ENFORCEMENT = "Return one valid JSON object only. No markdown. No prose."


def openai_messages_to_bedrock(
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
) -> tuple[list[dict], list[dict]]:
    system_parts: list[str] = []
    bedrock_messages: list[dict] = []

    for msg in messages:
        role = (msg.get("role") or "").strip().lower()
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        if role not in ("user", "assistant"):
            raise LlmConfigurationError(f"Unsupported message role for Bedrock: {role!r}")
        bedrock_messages.append({"role": role, "content": [{"text": content}]})

    if json_mode:
        system_parts.append(_JSON_ENFORCEMENT)

    system_blocks = [{"text": part} for part in system_parts] if system_parts else []
    return system_blocks, bedrock_messages
