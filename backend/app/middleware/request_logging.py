from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = (request.headers.get("x-request-id") or "").strip() or str(uuid4())

        structlog.contextvars.bind_contextvars(request_id=request_id)
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
            )
            raise
        finally:
            # Prevent context leaks between requests.
            structlog.contextvars.clear_contextvars()

        response.headers.setdefault("X-Request-ID", request_id)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        status = response.status_code

        event = "request_completed"
        if status >= 500:
            _logger.error(event, method=request.method, path=request.url.path, status_code=status, duration_ms=elapsed_ms)
        elif status >= 400:
            _logger.warning(event, method=request.method, path=request.url.path, status_code=status, duration_ms=elapsed_ms)
        else:
            _logger.info(event, method=request.method, path=request.url.path, status_code=status, duration_ms=elapsed_ms)

        return response
