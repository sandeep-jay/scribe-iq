"""Shared helper: locate secret_patterns.py and load it as a module."""
from __future__ import annotations
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def _find_scanner() -> Path | None:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "secret_patterns.py",
        here.parent.parent / "scripts" / "secret_patterns.py",
    ]
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.getcwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        candidates.insert(0, Path(repo_root) / "scripts" / "secret_patterns.py")
    except Exception:
        pass
    for c in candidates:
        if c.is_file():
            return c
    return None


def load_scanner():
    path = _find_scanner()
    if path is None:
        return None
    spec = importlib.util.spec_from_file_location("secret_patterns", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["secret_patterns"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod
