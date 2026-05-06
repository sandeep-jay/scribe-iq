"""Shared-secret gate when BACKEND_API_KEY is set (no end-user SSO in Phase 1)."""

from __future__ import annotations

import secrets

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

_PUBLIC_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)

_log = structlog.get_logger(__name__)


def _unauthorized() -> Response:
    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})


def _auth_header_ok(request: Request, secret: str) -> bool:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if secrets.compare_digest(token, secret):
            return True
    xkey = request.headers.get("x-api-key")
    if xkey and secrets.compare_digest(xkey.strip(), secret):
        return True
    return False


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    """Optional shared-secret gate.

    When ``BACKEND_API_KEY`` is unset, this middleware is a no-op. When set, callers must present
    ``Authorization: Bearer`` or ``X-API-Key``. Denials are logged as ``api_key_denied`` (no secrets).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith(_PUBLIC_PREFIXES):
            _log.debug("api_key_public_path", path=path, method=request.method)
            return await call_next(request)

        settings = get_settings()
        key = (settings.backend_api_key or "").strip()
        if not key:
            _log.debug("api_key_auth_skipped", path=path, reason="no_backend_api_key")
            return await call_next(request)

        if not _auth_header_ok(request, key):
            rid = getattr(request.state, "request_id", None)
            _log.warning(
                "api_key_denied",
                path=path,
                method=request.method,
                request_id=rid,
                has_authorization=bool(request.headers.get("authorization")),
                has_x_api_key=bool(request.headers.get("x-api-key")),
            )
            return _unauthorized()

        _log.debug("api_key_auth_ok", path=path, method=request.method)
        return await call_next(request)
