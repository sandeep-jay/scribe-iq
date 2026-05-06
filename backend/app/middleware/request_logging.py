from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """PHI-safe access logging: path/method/status/duration only (no query string or body).

    Emits ``request_completed`` at INFO/WARN/ERROR by status class. Unhandled exceptions log
    ``request_failed`` with stack trace at ERROR.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = (request.headers.get("x-request-id") or "").strip() or str(uuid4())
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        # DEBUG: first hop after CORS; see main.py middleware order (last-added runs first).
        _logger.debug(
            "request_received",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            _logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=elapsed_ms,
                request_id=request_id,
            )
            structlog.contextvars.clear_contextvars()
            raise

        response.headers.setdefault("X-Request-ID", request_id)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        status = response.status_code
        base = dict(
            method=request.method,
            path=request.url.path,
            status_code=status,
            duration_ms=elapsed_ms,
            request_id=request_id,
        )
        if status >= 500:
            _logger.error("request_completed", **base)
        elif status >= 400:
            _logger.warning("request_completed", **base)
        else:
            _logger.info("request_completed", **base)

        structlog.contextvars.clear_contextvars()
        return response
