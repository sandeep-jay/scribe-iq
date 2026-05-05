# Scribe-IQ Backend

FastAPI service for the clinical RAG demo. See [`../roadmap/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md`](../roadmap/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md).

## Setup

From repo root:

```bash
docker compose up -d
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # edit keys when using LLM/embeddings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Smoke test:

```bash
curl http://localhost:8000/health
```

## Database migrations (Alembic)

Requires Postgres reachable at `DATABASE_URL` (see `.env.example`).

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

If you see `FATAL: role "rag" does not exist`, you are not hitting the Compose database (or Compose is down). Typical fixes:

- Ensure **`docker compose up -d`** from the **repo root** is running **this** compose file.
- Confirm another Postgres is not occupying **5432** (`brew services list`, or stop local Postgres briefly).

## Postgres host port (`5433`)

Compose maps **host `5433`** → container `5432`. Use:

`DATABASE_URL=postgresql://rag:rag_dev_password@127.0.0.1:5433/rag_dev`

So Alembic and local tools talk to **Docker Postgres**, not another server bound to `:5432` (Homebrew Postgres, etc.). After changing compose ports, recreate the stack:

```bash
cd ..   # repo root
docker compose down && docker compose up -d
```

Existing data stays in volume `scribe_iq_pgdata` unless you remove the volume.

## Load corpus into Postgres (`T3`)

From `backend/` (Postgres reachable via `DATABASE_URL`, repo root sibling of `backend/`):

```bash
pip install -e .
python -m scripts.load_corpus              # upsert corpus (idempotent via ON CONFLICT)
python -m scripts.load_corpus --truncate   # wipe patients/notes first
python -m scripts.load_corpus --embed      # requires OPENAI_API_KEY; fills VECTOR(1536)
```

Alternatively: `scribe-load-corpus`.

Expected counts match `data/clinical_corpus_v2/manifest.json` (demo: ~19 patients, ~269 notes).

## Read API (T4)

- `GET /patients?domain=clinical&limit=50&offset=0` — roster + aggregate note counts / last encounter date  
- `GET /patients/{id}` — internal UUID **or** Synthea `external_id`; includes `latest_longitudinal` blob + recent note previews  
- `GET /notes/{uuid}` — full structured note/transcript/longitudinal payloads (`embedding_present` flag)

Swagger: `http://localhost:8000/docs` while `uvicorn` is running.

**Tip:** Postgres `json/jsonb` can surface as Python `str` via asyncgp; callers always receive parsed JSON objects in responses.

## Meeting prep (patient chart)

- Endpoint: `GET /patients/{id}/meeting-prep?domain=clinical&refresh=false`.
- Requires `GROQ_API_KEY` (same Groq stack as chat generation paths).
- Cached row in `patient_meeting_prep` (see Alembic `20260504_002`).
- Disable with `MEETING_PREP_ENABLED=false`.

## Responsible AI Control Center (audit + admin)

- **Migration:** `20260505_003` → table **`ai_interactions`** (run `alembic upgrade head`).
- **Env:** `RESPONSIBLE_AI_ADMIN_ENABLED=true` registers **`GET /admin/responsible-ai/*`** (metrics, interactions list/detail, safety-flags, model-usage) and sets **`responsible_ai_admin_enabled`** on **`GET /health`**. When `false`, admin routes are omitted (**404**).
- **Wiring:** `POST /chat`, `GET /patients/{id}/meeting-prep`, and `POST /notes/generate` write audit rows via `app/responsible_ai/` and may return **`audit` / `ai_audit`** metadata. Full inventory: **`reference-docs/SCRIBE_IQ_IMPLEMENTED_BASELINE.md`**.

## RAG chat status

`POST /chat` stays **503** until at least one `notes.embedding` exists for the domain. This sprint intentionally treats embeddings as optional; use meeting prep for AI narrative on charts.

