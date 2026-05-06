"""Leveled CLI logging for data_prep scripts.

Logs go to **stderr** so stdout stays available for machine-readable prints or shell
pipelines (``script.py > out.json`` captures only intentional stdout).

* ``--verbose`` / ``-v``: DEBUG — branch decisions, source selection, row previews.
* default: INFO — phase milestones and counts.
* ``--quiet`` / ``-q``: WARNING+ — errors and recoverable anomalies only.
* ``--log-json``: one JSON object per line (timestamps + level), still on stderr.

Prefer lengths/counts over raw clinical text; reserve full text for local DEBUG only.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_cli_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_json: bool = False,
) -> None:
    if verbose and quiet:
        raise ValueError("Cannot combine --verbose and --quiet")
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    if log_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger(__name__).debug(
        "cli_logging_configured verbose=%s quiet=%s log_json=%s effective=%s",
        verbose,
        quiet,
        log_json,
        logging.getLevelName(level),
    )


def add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logs")
    parser.add_argument("-q", "--quiet", action="store_true", help="Warnings and errors only")
    parser.add_argument("--log-json", action="store_true", help="JSON logs on stderr")


def logging_args_from_ns(ns: argparse.Namespace) -> dict[str, bool]:
    return {
        "verbose": bool(getattr(ns, "verbose", False)),
        "quiet": bool(getattr(ns, "quiet", False)),
        "log_json": bool(getattr(ns, "log_json", False)),
    }
