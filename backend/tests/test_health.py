from __future__ import annotations


def test_health_returns_expected_flags(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")

    supplied = "test-req-123"
    response2 = client.get("/health", headers={"X-Request-ID": supplied})
    assert response2.status_code == 200
    assert response2.headers.get("X-Request-ID") == supplied
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "scribe-iq-backend"
    assert "responsible_ai_admin_enabled" in payload
    assert "api_auth_configured" in payload
    assert payload["llm_provider"] in ("groq", "azure_openai", "bedrock")
    assert "llm_configured" in payload
    assert payload["llm_json_mode"] in ("native", "prompt_enforced", "unavailable")
    assert "embedding_provider" in payload
    assert "embedding_configured" in payload
    assert "embedding_model" in payload
    assert payload["embedding_dim"] == 1536
