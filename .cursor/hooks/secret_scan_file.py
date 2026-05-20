#!/usr/bin/env python3
"""Cursor hook: preToolUse for Write/Edit/StrReplace/MultiEdit.

Refuses (asks confirmation for) edits that would write a real-looking secret
into any file, and refuses edits to .env files that are not .env.example or
.env.test.
"""
from __future__ import annotations

import json
import os
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

    inp = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(inp, dict):
        _allow()

    target_path = ""
    for k in ("path", "filePath", "file_path", "target_file", "targetFile"):
        v = inp.get(k)
        if isinstance(v, str):
            target_path = v
            break

    if target_path:
        base = os.path.basename(target_path)
        if base == ".env" or (base.startswith(".env.") and base not in (".env.example", ".env.test")):
            print(json.dumps({
                "permission": "ask",
                "user_message": (
                    f"Cursor security hook: about to write to {target_path}. "
                    ".env files often contain real secrets and should not be edited "
                    "by the agent. Confirm to proceed."
                ),
                "agent_message": (
                    f"Local security hook: target path {target_path} looks like a "
                    ".env secrets file. Do not write real secrets here; edit "
                    ".env.example with placeholders instead."
                ),
            }))
            sys.exit(0)

    candidates: list[str] = []

    def collect_strings(value, *, key_name: str = "") -> None:
        # Scan proposed new content and patch payloads. Skip old_string because
        # it may contain a pre-existing secret the hook cannot prevent and the
        # agent may need to replace it with a placeholder.
        if key_name in {"old_string", "oldString"}:
            return
        if isinstance(value, str):
            if value.strip():
                candidates.append(value)
            return
        if isinstance(value, dict):
            for k, v in value.items():
                collect_strings(v, key_name=str(k))
            return
        if isinstance(value, list):
            for item in value:
                collect_strings(item)

    collect_strings(inp)
    merged = "\n".join(candidates)
    if not merged.strip():
        _allow()

    mod = load_scanner()
    if mod is None:
        _allow()

    findings = mod.find_secrets(merged)
    if not findings:
        _allow()

    names = sorted({f.description for f in findings})
    joined = ", ".join(names)
    where = target_path or "the file"
    print(json.dumps({
        "permission": "ask",
        "user_message": (
            f"Cursor security hook: this edit would write content that looks like a "
            f"real secret ({joined}) to {where}. Confirm to proceed."
        ),
        "agent_message": (
            f"Local security hook flagged proposed file content as containing "
            f"secret-like material ({joined}). Replace with a placeholder before writing."
        ),
    }))


if __name__ == "__main__":
    main()
