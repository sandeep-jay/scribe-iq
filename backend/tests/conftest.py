from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_conn
from app.main import create_app


class _DummyPool:
    async def close(self) -> None:
        return None


class FakeConn:
    def __init__(self) -> None:
        now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
        self.rows = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "request_id": "req-1",
                "interaction_type": "chat",
                "patient_id": "P001",
                "note_id": None,
                "model_provider": "groq",
                "model_name": "llama-3.3-70b-versatile",
                "prompt_version": "v1",
                "status": "success",
                "latency_ms": 120,
                "created_at": now,
                "governance_json": {"cached": False},
                "citations_json": [{"note_id": "n-1"}],
                "retrieved_sources_json": [{"source": "note"}],
                "safety_flags_json": [],
                "output_redacted_preview": "preview 1",
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "request_id": "req-2",
                "interaction_type": "meeting_prep",
                "patient_id": "P002",
                "note_id": None,
                "model_provider": "groq",
                "model_name": "llama-3.3-70b-versatile",
                "prompt_version": "v1",
                "status": "degraded",
                "latency_ms": 180,
                "created_at": now,
                "governance_json": {"cached": False},
                "citations_json": [],
                "retrieved_sources_json": [{"source": "note"}, {"source": "note"}],
                "safety_flags_json": [{"code": "MISSING_CITATION"}],
                "output_redacted_preview": "preview 2",
            },
        ]

    async def fetch(self, query: str, *args):
        if "FROM ai_interactions" in query and "ORDER BY created_at DESC" in query:
            limit = args[-2]
            offset = args[-1]
            return self.rows[offset : offset + limit]
        return []

    async def fetchval(self, query: str, *args):
        if "SELECT COUNT(*)::bigint FROM ai_interactions" in query:
            return len(self.rows)
        return 0


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("RESPONSIBLE_AI_ADMIN_ENABLED", "true")
    import app.config as config_module

    config_module._settings = None
    yield
    config_module._settings = None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    async def _fake_create_pool(_database_url: str):
        return _DummyPool()

    monkeypatch.setattr("app.main.asyncpg.create_pool", _fake_create_pool)

    app = create_app()

    async def _override_get_conn():
        yield FakeConn()

    app.dependency_overrides[get_conn] = _override_get_conn
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings():
    return get_settings()
