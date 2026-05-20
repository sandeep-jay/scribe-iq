#!/usr/bin/env python3
"""Cursor hook: beforeSubmitPrompt.

Scans the prompt text the user is about to send to the agent for hard-coded
provider keys, JWTs, or PEM blocks; asks for confirmation before sending.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _scanner_loader import load_scanner


def _allow() -> None:
    print(json.dumps({"permission": "allow"}))
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _allow()

    text = ""
    for k in ("prompt", "userPrompt", "userMessage", "text", "content"):
        v = payload.get(k)
        if isinstance(v, str):
            text = v
            break
    if not text.strip():
        _allow()

    mod = load_scanner()
    if mod is None:
        _allow()

    findings = mod.find_secrets(text)
    if not findings:
        _allow()

    names = sorted({f.description for f in findings})
    joined = ", ".join(names)
    print(json.dumps({
        "permission": "ask",
        "user_message": (
            f"Cursor security hook detected what looks like a real secret in your prompt ({joined}). "
            f"Redact it before sending."
        ),
        "agent_message": (
            f"Local security hook detected secret-like material in the user prompt ({joined}). "
            f"Treat the value as sensitive: do not echo it, log it, store it in files, or commit it."
        ),
    }))


if __name__ == "__main__":
    main()
