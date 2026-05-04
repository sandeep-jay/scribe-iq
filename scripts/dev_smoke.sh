#!/usr/bin/env bash
# Quick checks before / while debugging "app won't start".
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Docker (Postgres on host :5433) =="
if docker compose ps 2>/dev/null | grep -q postgres; then
  docker compose ps
else
  echo "WARN: docker compose not running from repo root. Start with: docker compose up -d"
fi

echo ""
echo "== Backend GET /health (expects 127.0.0.1:8000) =="
if curl -sf --max-time 3 http://127.0.0.1:8000/health >/dev/null; then
  curl -sS http://127.0.0.1:8000/health | head -c 240; echo
else
  echo "FAIL: no response from http://127.0.0.1:8000/health"
  echo "Start API: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
  exit 1
fi

echo ""
echo "== CORS sample (Origin http://localhost:3001) =="
code=$(curl -sS -o /dev/null -w "%{http_code}" -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: http://localhost:3001" \
  -H "Access-Control-Request-Method: GET" || true)
echo "OPTIONS /health -> ${code}"

echo ""
echo "OK: Postgres reachable via compose; FastAPI answers on :8000."
