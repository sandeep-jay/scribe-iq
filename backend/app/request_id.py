"""Correlation ID shared between middleware and route handlers.

``RequestLoggingMiddleware`` sets ``request.state.request_id`` so audit rows and
logs match ``X-Request-ID`` even when the client omits the header.

Resolution order:

1. ``request.state.request_id`` (set by ``RequestLoggingMiddleware``)
2. ``X-Request-ID`` header (client-provided)
3. A freshly generated UUID (last resort; prefer middleware so response header matches audits)
"""

from __future__ import annotations

from uuid import uuid4

from starlette.requests import Request


def get_request_id(request: Request) -> str:
    """Return the active request id (middleware-bound, then header, then new UUID)."""
    rid = getattr(request.state, "request_id", None)
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    header = (request.headers.get("x-request-id") or "").strip()
    if header:
        return header
    return str(uuid4())
