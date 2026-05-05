from __future__ import annotations


def test_health_returns_expected_flags(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "scribe-iq-backend"
    assert "responsible_ai_admin_enabled" in payload
    assert "api_auth_configured" in payload
