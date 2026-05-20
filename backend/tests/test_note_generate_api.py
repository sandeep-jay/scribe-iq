from __future__ import annotations

from unittest.mock import AsyncMock
import uuid

import pytest

from app.config import get_settings
from app.llm.types import LlmCompletionResult


def test_note_generate_invalid_json_returns_502(client, monkeypatch):
    monkeypatch.setenv("NOTE_GENERATION_ENABLED", "true")
    import app.config as config_module

    config_module._settings = None

    bad = LlmCompletionResult(
        text="not-json",
        latency_ms=1,
        provider="groq",
        model="m",
        prompt_tokens=None,
        completion_tokens=None,
    )

    monkeypatch.setattr(
        "app.api.note_generate.chat_json_completion",
        AsyncMock(return_value=bad),
    )
    monkeypatch.setattr(
        "app.api.note_generate.resolve_patient_id",
        AsyncMock(return_value=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    )

    resp = client.post(
        "/notes/generate",
        json={"patient_id": "P001", "transcript": "Patient reports headache."},
    )
    assert resp.status_code == 502
    assert "LLM structured output rejected" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_audit_note_row_uses_completion_provider(monkeypatch):
    from app.api.note_generate import _audit_note_row

    captured = {}

    async def _capture(conn, **kwargs):
        captured.update(kwargs)
        return "33333333-3333-3333-3333-333333333333"

    monkeypatch.setattr("app.api.note_generate.insert_ai_interaction", _capture)

    completion = LlmCompletionResult(
        text="{}",
        latency_ms=3,
        provider="azure_openai",
        model="gpt-4o-mini",
        prompt_tokens=1,
        completion_tokens=2,
    )
    await _audit_note_row(
        conn=None,  # type: ignore[arg-type]
        request_id="req",
        patient_uuid=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        note_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        completion=completion,
        structured_blob={"summary": "ok"},
        transcript="hello",
        settings=get_settings(),
    )
    assert captured["model_provider"] == "azure_openai"
    assert captured["model_name"] == "gpt-4o-mini"
