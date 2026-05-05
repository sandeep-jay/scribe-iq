from __future__ import annotations

from conftest import FakeConn


def test_chat_returns_503_when_embeddings_missing(client_with_conn):
    with client_with_conn(FakeConn(indexed=False)) as tc:
        r = tc.post("/chat", json={"domain": "clinical", "message": "hello", "conversation": [], "top_k": 3})
    assert r.status_code == 503


def test_chat_rejects_whitespace_domain(client_with_conn):
    with client_with_conn(FakeConn(indexed=True)) as tc:
        r = tc.post("/chat", json={"domain": " clinical ", "message": "hello", "conversation": [], "top_k": 3})
    assert r.status_code == 400
