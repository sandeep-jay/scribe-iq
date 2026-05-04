"""Normalize Synthea CSV person labels for demos (strip numeric suffix tokens).

Synthea v3 emits tokens like Kenna183 and Luis923 — unique but ugly for human-facing UI.
"""

from __future__ import annotations

import re

_LEADING_PUNC = '(\"\'[{'
_TRAILING_PUNC = ".,;:)]}!?'%"


def prettify_synthea_token(token: str) -> str:
    """Strip a trailing numeric run from tokens like Alicia412 -> Alicia."""

    if not token:
        return token

    punct_lead = ""
    punct_trail = ""
    body = token

    while body and body[0] in _LEADING_PUNC:
        punct_lead += body[0]
        body = body[1:]
    while body and body[-1] in _TRAILING_PUNC:
        punct_trail = body[-1] + punct_trail
        body = body[:-1]

    if "-" in body:
        merged = "-".join(prettify_synthea_token(part) for part in body.split("-"))
        return f"{punct_lead}{merged}{punct_trail}"

    name_body = body
    m = re.fullmatch(r"([A-Za-z][A-Za-z'.\-]{0,64}?)(\d{1,})", name_body)
    if m:
        letters = "".join(ch for ch in (m.group(1) or "") if ch.isalpha())
        if len(letters) >= 2:
            name_body = letters

    return f"{punct_lead}{name_body}{punct_trail}"


def prettify_synthea_display_name(display: str) -> str:
    if not isinstance(display, str):
        display = str(display or "")
    s = display.strip()
    if not s:
        return ""
    return " ".join(prettify_synthea_token(t) for t in s.split())

