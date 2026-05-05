from __future__ import annotations


def test_list_interactions_pagination_contract(client):
    response = client.get("/admin/responsible-ai/interactions", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["request_id"] == "req-2"
