# Scribe-IQ Backend

FastAPI service for the clinical RAG demo. See [`../docs/architecture/IMPLEMENTED_BASELINE.md`](../docs/architecture/IMPLEMENTED_BASELINE.md) (historical v1 plan: [`../docs/archive/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md`](../docs/archive/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md)).

Architecture hub: [`docs/architecture/README.md`](../docs/architecture/README.md) · As-built detail: [`docs/architecture/IMPLEMENTED_BASELINE.md`](../docs/architecture/IMPLEMENTED_BASELINE.md).

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

Logging:

- `LOG_LEVEL` controls verbosity (default: `INFO`; set `DEBUG` for detailed checkpoints).
- `LOG_JSON=true` switches logs to JSON (recommended in production).
- DB pool tuning: `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_COMMAND_TIMEOUT_S`.
- Event taxonomy follows `*_started`, `*_validated`, `*_failed`, `*_succeeded` where practical.
- Each response includes an `X-Request-ID` header for correlation with frontend `x-request-id` logs.
- PHI policy: do **not** log transcript/note bodies; log IDs/counts/status/timings only.


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
python -m scripts.load_corpus --embed      # requires configured embedding provider credentials; fills VECTOR per EMBED_DIM
```

Alternatively: `scribe-load-corpus`.

Expected counts match `data/clinical_corpus_v2/manifest.json` (demo: ~19 patients, ~269 notes).

## Read API (T4)

- `GET /patients?domain=clinical&limit=50&offset=0` — roster + aggregate note counts / last encounter date  
- `GET /patients/{id}` — internal UUID **or** Synthea `external_id`; includes `latest_longitudinal` blob + recent note previews  
- `GET /notes/{uuid}` — full structured note/transcript/longitudinal payloads (`embedding_present` flag)

Swagger: `http://localhost:8000/docs` while `uvicorn` is running.

**Tip:** Postgres `json/jsonb` can surface as Python `str` via asyncgp; callers always receive parsed JSON objects in responses.


## LLM providers

- **Demo:** `LLM_PROVIDER=groq` + `GROQ_API_KEY`
- **Enterprise:** `azure_openai` or `bedrock` — see `backend/.env.example` and [`docs/guides/LLM_AND_EMBEDDING_PROVIDERS.md`](../docs/guides/LLM_AND_EMBEDDING_PROVIDERS.md).

## Meeting prep (patient chart)

- Endpoint: `GET /patients/{id}/meeting-prep?domain=clinical&refresh=false`.
- Requires a configured LLM provider (`LLM_PROVIDER` plus provider credentials). Without one, the route returns a deterministic offline summary.
- Cached row in `patient_meeting_prep` (see Alembic `20260504_002`).
- Disable with `MEETING_PREP_ENABLED=false`.
- Performance: cache-hit reads now use a lightweight notes fingerprint check before returning, avoiding full bundle rebuild on hot path.

### Logging events (backend)

- **INFO**: request accepted/completed, cache hit/miss, provider success, audit persistence outcomes.
- **DEBUG** (`LOG_LEVEL=DEBUG`): branch decisions (scope/cache/replace-vs-create), token/latency metadata, source-selection checkpoints.
- **WARN/ERROR**: degraded fallback paths, expected provider outages, validation/auth failures, unexpected exceptions.

### Performance notes

- Meeting-prep cached path uses fast fingerprint validation and avoids full bundle rebuild on cache hits.
- External provider calls can vary widely in latency; cached reads should remain low-single-digit milliseconds locally.
- ANN retrieval index migration: `20260506_005` creates `ix_notes_embedding_ivfflat_cosine` for `/chat` vector search.

## Responsible AI Control Center (audit + admin)

- **Migration:** `20260505_003` → table **`ai_interactions`** (run `alembic upgrade head`).
- **Env:** `RESPONSIBLE_AI_ADMIN_ENABLED=true` registers **`GET /admin/responsible-ai/*`** (metrics, interactions list/detail, safety-flags, model-usage) and sets **`responsible_ai_admin_enabled`** on **`GET /health`**. When `false`, admin routes are omitted (**404**).
- **Wiring:** `POST /chat`, `GET /patients/{id}/meeting-prep`, and `POST /notes/generate` write audit rows via `app/responsible_ai/` and may return **`audit` / `ai_audit`** metadata. Full inventory: **`docs/architecture/IMPLEMENTED_BASELINE.md`**.

## RAG chat status


Embedding providers are also configurable for RAG retrieval and generated note vectors. Set
`EMBEDDING_PROVIDER=openai`, `azure_openai`, `bedrock`, or `none`. Azure reuses
`AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` plus `AZURE_EMBEDDING_DEPLOYMENT`;
Bedrock uses `AWS_BEDROCK_EMBEDDING_MODEL_ID` (use `amazon.titan-embed-text-v1` for the
existing `EMBED_DIM=1536` schema). Switching providers requires re-running
`scribe-load-corpus --embed` so stored vectors and query vectors share the same space.

`POST /chat` stays **503** until at least one `notes.embedding` exists for the domain. This sprint intentionally treats embeddings as optional; use meeting prep for AI narrative on charts.



## Test and lint (TDD)

Adopt Red -> Green -> Refactor for backend changes: write/update a failing test first, implement the minimal fix, then refactor.

Run local quality checks:

```bash
cd backend
source .venv/bin/activate
tox -e lint,py311          # ruff lint + unit/integration tests (CI parity)
tox -e lint                # ruff lint only (fast)
tox -e format-check        # advisory: ruff format --check
tox -e format              # apply ruff formatting and autofixes
```

CI runs `tox -e lint` as a dedicated, fast-failing job (`backend-lint`) before
`tox -e py311` (`backend`), so style regressions surface within a minute.


Documentation map (repository-wide): [`docs/README.md`](../docs/README.md) · [`docs/architecture/README.md`](../docs/architecture/README.md).
