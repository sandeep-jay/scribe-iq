#!/usr/bin/env bash
# One-shot installer for the versioned hooks under .githooks/.
# Idempotent; safe to re-run.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

echo "Configured git core.hooksPath -> .githooks"
echo "Hooks installed: $(ls .githooks | tr '\n' ' ')"
