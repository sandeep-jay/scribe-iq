# Quickstart

One supported path to a working system. Follow this top to bottom and you will have a working UI in about ten minutes.

For exact API and schema detail, see [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md). For diagrams and flags, see [`docs/overview/SYSTEM_OVERVIEW.md`](../overview/SYSTEM_OVERVIEW.md) (optional reading after you are running).

> **Note.** Groq (for completions) and OpenAI (for embeddings) are the **simplest local defaults** and what this quickstart assumes. The same code paths support Azure OpenAI and Amazon Bedrock — see [`LLM_AND_EMBEDDING_PROVIDERS.md`](./LLM_AND_EMBEDDING_PROVIDERS.md) for the full provider configuration matrix.

---

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Docker | recent | Runs Postgres 16 with pgvector |
| Python | 3.11+ | Backend runtime |
| Node | 20 (`.nvmrc`) | Frontend runtime |
| `nvm` | optional | `nvm use` picks the right Node |

Optional API keys:

| Key | Unlocks |
|-----|---------|
| `GROQ_API_KEY` | Pre-meeting summaries, structured note generation, chat completions |
| `OPENAI_API_KEY` | Embeddings for RAG chat (requires `scribe-load-corpus --embed`) |

No key is required to see the patient list, charts, and encounter viewer.

---

## Minimum working system

These commands assume you are at the repository root and the pre-built corpus exists under `data/clinical_corpus_v2/`.

```bash
# 1. Start Postgres with pgvector on host port 5433
docker compose up -d

# 2. Install backend and apply migrations
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head

# 3. Load the corpus into Postgres
scribe-load-corpus

# 4. Run the API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
# 5. Run the frontend
cd frontend
nvm use         # Node 20 from .nvmrc
npm install
npm run dev
```

Open <http://localhost:3000>. You should see the patient list immediately.

---

## Optional capabilities (same install, more keys)

**No keys:** patient list, chart, encounter viewer, care timeline; chat tab explains missing embeddings; meeting prep shows a placeholder.

**`GROQ_API_KEY` in `backend/.env`:** pre-meeting summaries; set `NOTE_GENERATION_ENABLED=true` for the generate-note panel.

**`OPENAI_API_KEY` + reload with embeddings:**

```bash
# append to backend/.env, then:
scribe-load-corpus --embed
```

Restart the API — RAG chat returns answers with citations instead of 503.

**Responsible AI admin:** `RESPONSIBLE_AI_ADMIN_ENABLED=true` (backend) and `NEXT_PUBLIC_SCRIBE_ADMIN_UI=true` (frontend), restart both — Control Center nav and `/admin/responsible-ai`.

---

## Smoke check

```bash
bash scripts/dev_smoke.sh
```

Expected: Postgres healthy via Compose; `GET /health` returns JSON with capability flags.

---

## Troubleshooting

**Port 5433 already in use.** Stop the conflicting Postgres (often Homebrew: `brew services stop postgresql`) or change the host mapping in [`docker-compose.yml`](../../docker-compose.yml).

**`FATAL: role "rag" does not exist` during `alembic upgrade head`.** You are not hitting Compose Postgres — confirm `docker compose ps` and that `DATABASE_URL` in `backend/.env` uses `127.0.0.1:5433`.

**Chat 503 "No embeddings in the database".** Expected until the configured embedding provider is set (`EMBEDDING_PROVIDER` plus credentials in `backend/.env`) **and** `scribe-load-corpus --embed` has been run against that provider. See [`LLM_AND_EMBEDDING_PROVIDERS.md`](./LLM_AND_EMBEDDING_PROVIDERS.md) for the full embedding-rebuild workflow. Meeting prep with Groq is an LLM-only feature and works without embeddings.

**More:** backend port, CORS, API base URL — see [`backend/README.md`](../../backend/README.md) and [`frontend/README.md`](../../frontend/README.md).

---

## Rebuilding the corpus

See [`data_prep/README.md`](../../data_prep/README.md) (requires `synthea-with-dependencies.jar` at repo root).
