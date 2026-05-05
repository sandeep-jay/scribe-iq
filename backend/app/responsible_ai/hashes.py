"""SHA-256 helpers for audit hashes."""

from __future__ import annotations

import hashlib


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = data
    return hashlib.sha256(raw).hexdigest()
