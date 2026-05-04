"""Shared-secret gate when BACKEND_API_KEY is set (no end-user SSO in Phase 1)."""

from __future__ import annotations

import secrets

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
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith(_PUBLIC_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        key = (settings.backend_api_key or "").strip()
        if not key:
            return await call_next(request)

        if not _auth_header_ok(request, key):
            return _unauthorized()

        return await call_next(request)
