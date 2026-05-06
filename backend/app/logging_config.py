"""Centralized structured logging configuration (structlog + stdlib).

This module is intentionally imported early from app startup to ensure:
- consistent log formatting (console in dev, JSON in production)
- uvicorn and stdlib logs route through the same formatter

Call sites must not log request bodies, transcripts, or other PHI; use metadata and ids only.

Verbosity: set ``LOG_LEVEL=DEBUG`` for detailed per-request checkpoints in route handlers; keep
``INFO`` in production unless diagnosing an incident.
"""

from __future__ import annotations

import logging
from logging.config import dictConfig

import structlog


_configured = False


def _normalize_level(level: str) -> str:
    lv = (level or "").strip().upper()
    return lv if lv else "INFO"


def configure_logging(settings) -> None:
    """Configure structlog + stdlib logging.

    Idempotent: safe to call multiple times (e.g. in tests).
    """

    global _configured
    if _configured:
        return

    level = _normalize_level(getattr(settings, "log_level", "INFO"))
    log_json = bool(getattr(settings, "log_json", False))

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
    ]

    renderer: structlog.types.Processor
    if log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    formatter = {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": renderer,
        "foreign_pre_chain": pre_chain,
    }

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": formatter},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                }
            },
            "root": {"handlers": ["default"], "level": level},
            "loggers": {
                # Make uvicorn logs consistent with app logs.
                "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
                "uvicorn.access": {"handlers": ["default"], "level": level, "propagate": False},
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            timestamper,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Avoid duplicate handlers if something configured logging earlier.
    logging.captureWarnings(True)

    _configured = True
