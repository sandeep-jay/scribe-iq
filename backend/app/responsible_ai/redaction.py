"""Demo-safe minimization for audit previews (not a formal de-id engine)."""

from __future__ import annotations

import re


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
_MRNISH = re.compile(r"\b(?:MRN|medical record)[ #:]*[A-Za-z0-9-]{4,}\b", re.I)
_UUID_LIKE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I
)


def redact_preview(text: str | None, *, max_chars: int = 1600) -> str | None:
    if text is None:
        return None
    s = text.strip().replace("\r\n", "\n")
    if not s:
        return ""
    s = _EMAIL.sub("[EMAIL]", s)
    s = _PHONE.sub("[PHONE]", s)
    s = _MRNISH.sub("[ID]", s)
    # Keep note UUID citations like [note:<uuid>] readable but mask raw UUIDs elsewhere.
    s = _UUID_LIKE.sub("[UUID]", s)
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 3].rstrip() + "..."
