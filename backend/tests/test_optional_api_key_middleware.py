from __future__ import annotations


def test_auth_not_required_without_backend_key(monkeypatch, client_with_conn):
    from conftest import FakeConn

    monkeypatch.setenv("BACKEND_API_KEY", "")
    with client_with_conn(FakeConn()) as tc:
        r = tc.get("/admin/responsible-ai/interactions")
        assert r.status_code == 200


def test_auth_required_with_backend_key(monkeypatch, client_with_conn):
    from conftest import FakeConn

    monkeypatch.setenv("BACKEND_API_KEY", "secret-key")
    with client_with_conn(FakeConn()) as tc:
        blocked = tc.get("/admin/responsible-ai/interactions")
        assert blocked.status_code == 401

        ok = tc.get("/admin/responsible-ai/interactions", headers={"Authorization": "Bearer secret-key"})
        assert ok.status_code == 200
