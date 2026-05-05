from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
import os

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_conn
from app.main import create_app


class _DummyPool:
    async def close(self) -> None:
        return None


class FakeConn:
    def __init__(self, rows: list[dict] | None = None, total: int | None = None, indexed: bool = True) -> None:
        now = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
        self.rows = rows if rows is not None else [
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
        self.total = len(self.rows) if total is None else total
        self.indexed = indexed

    async def fetch(self, query: str, *args):
        if "FROM ai_interactions" in query and "ORDER BY created_at DESC" in query:
            limit = args[-2]
            offset = args[-1]
            return self.rows[offset : offset + limit]
        if "FROM notes n" in query and "ORDER BY n.embedding" in query:
            return []
        return []

    async def fetchval(self, query: str, *args):
        if "SELECT COUNT(*)::bigint FROM ai_interactions" in query:
            return self.total
        if "SELECT EXISTS" in query and "FROM notes" in query:
            return self.indexed
        return 0

    async def fetchrow(self, query: str, *args):
        return None


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
def client_with_conn(monkeypatch: pytest.MonkeyPatch):
    def _make(fake_conn: FakeConn) -> TestClient:
        async def _fake_create_pool(_database_url: str):
            return _DummyPool()

        monkeypatch.setattr("app.main.asyncpg.create_pool", _fake_create_pool)
        app = create_app()

        async def _override_get_conn():
            yield fake_conn

        app.dependency_overrides[get_conn] = _override_get_conn
        return TestClient(app)

    return _make


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def integration_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or "postgresql://rag:rag_dev_password@127.0.0.1:5433/rag_dev"


@pytest.fixture
async def pg_conn(integration_database_url: str) -> AsyncGenerator[asyncpg.Connection, None]:
    try:
        conn = await asyncpg.connect(integration_database_url)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Integration database unavailable: {exc}")
    try:
        yield conn
    finally:
        await conn.close()
