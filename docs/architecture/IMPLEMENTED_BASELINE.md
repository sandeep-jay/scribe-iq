# Scribe IQ — implemented baseline (current code)

This document inventories **what exists in the repository today** (application, backend API, database, tooling). It complements **plans and roadmaps** (`docs/roadmap/`, coding agent plans) by describing the **current** behavior only.

**Last reviewed:** 2026-05-05 (against the repo tree: `backend/`, `frontend/`, `docker-compose.yml`, `data_prep/`, `docs/architecture/`, `docs/reference/`).

---

## Functional summary (what works today)

Short functional read of the baseline; sections below spell out routes, files, and schema.

### End-user and demo flows

1. **Browse patients** — Paginated roster with sorting, filter chips, advanced filter area, and corpus stats. Search filters the list and is reflected in the URL as **`?q=`** on `/patients`.

2. **Open a patient chart** — Demographics/metadata, longitudinal snippets and medication hints, a **pre-meeting summary** (Groq-backed when configured) with refresh, cached vs degraded behavior, and model metadata.

3. **Explore clinical history** — **Read**, **Sources**, and **Codes & map** tabs; a **care timeline** with horizontal scroll; **encounter list** with UI pagination (10 per page); for many visits, the timeline can use **month buckets** so the strip stays usable.

4. **Open one encounter** — Full encounter/note view from **`GET /notes/{id}`**: transcript, structured note, entities, longitudinal context, and whether an embedding exists.

5. **Generate a structured note from a transcript** — **Generate note** on the chart accepts transcript (plus optional specialty/session fields), checks **backend health** and **`NOTE_GENERATION_ENABLED`**, then calls **`POST /notes/generate`** to create or update a note via the LLM when enabled.

6. **RAG chat** — **`POST /chat`** runs vector search over stored note embeddings and returns an answer with **citations**. If there are **no embeddings** for the domain, the API returns **503** and the UI should surface that (chat stays optional until embeddings are loaded).

7. **In-app docs pointer** — `/docs` points readers to in-repo Markdown; canonical map **`docs/README.md`**, architecture hub **`docs/architecture/README.md`**, plus **`docs/roadmap/`** and **`docs/reference/`**.

8. **App shell** — Responsive layout: sidebar (Patients, Chat, Docs) on larger breakpoints, mobile menu, **global patient search** in the header, **dark/light** theme.

9. **Responsible AI Control Center (when enabled)** — Each **`POST /chat`**, **`GET /patients/{id}/meeting-prep`**, and **`POST /notes/generate`** call can **record** a row in **`ai_interactions`** (hashes, redacted previews, governance JSON, latency/tokens where available) and return an **`audit` / `ai_audit`** block with **`interaction_id`** for traceability. **Admin REST APIs** under **`/admin/responsible-ai/*`** (gated by **`RESPONSIBLE_AI_ADMIN_ENABLED`**) expose metrics, interaction list/detail, safety-flag aggregates, and model-usage summaries. The Next.js app can show a **Responsible AI** nav entry and **`/admin/responsible-ai`** pages when **`NEXT_PUBLIC_SCRIBE_ADMIN_UI=true`**; chart/chat/meeting-prep surfaces may link “Why this…?” to an interaction detail page.

### Platform and operations (supporting behavior)

- **Docker Postgres + pgvector** for local development (host **5433**).
- **Alembic migrations** for `patients`, `notes` (including vector embeddings), and **`patient_meeting_prep`** cache.
- **Load corpus into the database** — `load_corpus` / `scribe-load-corpus` upserts from the built corpus; optional **truncate** and optional **OpenAI** embedding fill.
- **Offline corpus build** — `data_prep/` scripts produce the dataset the loader ingests (not invoked per HTTP request).
- **Optional API key** on the API (`BACKEND_API_KEY` with `X-API-Key` or Bearer) and **CORS** tuned for local/LAN demos (`CORS_RELAX_LOCAL`).
- **`GET /health`** reports configured capabilities (e.g. note generation, meeting prep, LLM provider, API auth, **Responsible AI admin** when `RESPONSIBLE_AI_ADMIN_ENABLED` is true).

### Not in this baseline (planned elsewhere)

- **Audio → transcript** (no `/transcribe`; no Whisper/GCP ASR in app code yet) — see `docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md` §12.
- **LangGraph**-style agent orchestration for notes.
- **Enterprise SSO / multi-tenant RBAC** beyond the optional shared API secret.

---

## 1. Repository layout (application-relevant)

| Area | Role |
|------|------|
| `frontend/` | Next.js (App Router) UI: patients, chart, encounter, chat, in-app docs pointer. |
| `backend/` | FastAPI API, Postgres access, LLM/embeddings helpers, Alembic migrations, corpus loader. |
| `docker-compose.yml` | Local **Postgres 16 + pgvector** (`pgvector/pgvector:pg16`), host port **5433**. |
| `data_prep/` | Canonical **corpus build** pipeline (Synthea + notes scripts `01`–`09`); see `data_prep/README.md` and `docs/reference/corpus_offline_pipeline_v2_brief.md`. |
| `data/` | Staging and corpus outputs (e.g. `data/staging/`); loader reads packaged corpus paths per `backend/scripts/load_corpus.py` and `backend/README.md`. |
| `scripts/dev_smoke.sh` | Quick Compose + `GET /health` smoke check. |
| `docs/roadmap/` | Product/UI/master plans (**not** a substitute for this inventory). |
| `docs/design/` | HTML UI mockups (`docs/design/mockups/`) and screenshot references (`docs/design/references/`). |

Root `README.md` summarizes run commands and high-level API behavior.

---

## 2. Infrastructure and runtime

### 2.1 Postgres (Docker)

- **Image:** `pgvector/pgvector:pg16`
- **Volume:** `scribe_iq_pgdata`
- **Credentials / DB:** `rag` / `rag_dev_password` / `rag_dev` (see `docker-compose.yml`)
- **Host port:** `5433` → container `5432` (avoids clashing with a local Postgres on `5432`)

### 2.2 Database schema (Alembic)

| Revision | Purpose |
|----------|---------|
| `20260504_001` | `patients`, `notes` with **pgvector** `embedding` column; JSONB metadata; indexes including GIN on `patients.metadata`. |
| `20260504_002` | `patient_meeting_prep` — cached **meeting prep** summary per patient (`summary_text`, model, prompt version, source fingerprint, `generated_at`). |
| `20260505_003` | **`ai_interactions`** — Responsible AI **audit** rows (request correlation, interaction type, patient/note linkage, model/provider, prompt/output hashes, redacted previews, JSONB governance + sources, latency/tokens, status, timestamps, indexes). |

Apply: `cd backend && alembic upgrade head` (with `DATABASE_URL` pointing at the Compose instance).

### 2.3 Corpus load (backend)

- **Script:** `backend/scripts/load_corpus.py` (console entry: `scribe-load-corpus`)
- **Modes:** upsert JSONL corpus; optional `--truncate`; optional `--embed` (OpenAI embeddings → `notes.embedding`)
- **Env:** `DATABASE_URL`, and for embeddings `OPENAI_API_KEY` (see `backend/README.md`)

---

## 3. Backend (FastAPI)

### 3.1 App entry and lifecycle

- **Module:** `app.main:create_app` / `app` instance
- **Lifespan:** creates an **asyncpg** pool from `Settings.database_url` and stores it on `app.state.db_pool`

### 3.2 Middleware and CORS

| Layer | Behavior |
|-------|----------|
| **`OptionalApiKeyMiddleware`** | If `BACKEND_API_KEY` is set, all routes except `/`, `/health`, `/docs`, `/redoc`, `/openapi.json` require `Authorization: Bearer <key>` or `X-API-Key: <key>`. If unset, no auth gate. |
| **CORS** | Origins from `CORS_ORIGINS` (comma-separated). If `CORS_RELAX_LOCAL=true`, also allows regex for `localhost` / `127.0.0.1` on any port and `192.168.*` (LAN demos). |

### 3.3 Configuration (`app.config.Settings`)

Notable environment-driven flags (see `backend/.env.example`):

- **`DATABASE_URL`**, **`BACKEND_API_KEY`** (optional)
- **LLM:** `LLM_PROVIDER` (`groq` \| `azure`), Groq/Azure OpenAI fields, `GROQ_API_KEY`, etc.
- **Embeddings:** `EMBEDDING_PROVIDER` (`openai` \| `azure` \| `none`), `OPENAI_API_KEY`, dimensions/model names
- **`NOTE_GENERATION_ENABLED`** — must be `true` for `POST /notes/generate` writes
- **`MEETING_PREP_ENABLED`** — toggles meeting prep path (default on in settings)
- **`RESPONSIBLE_AI_ADMIN_ENABLED`** — when `true`, mounts **`/admin/responsible-ai/*`** admin routes and exposes **`responsible_ai_admin_enabled`** on **`GET /health`**; when `false`, those routes are **not registered** (callers get **404**).

### 3.4 HTTP API (implemented routes)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + flags: `llm_provider`, `note_generation_enabled`, `meeting_prep_enabled`, `responsible_ai_admin_enabled`, `api_auth_configured`, etc. |
| `GET` | `/patients` | Paginated patient roster (`domain`, `limit`, `offset`); aggregates note counts / last session / specialty hints. |
| `GET` | `/patients/stats` | Corpus totals for a `domain`. |
| `GET` | `/patients/{patient_id}` | Chart payload: metadata, `latest_longitudinal`, medication hints, **note previews** list. |
| `GET` | `/patients/{patient_id}/meeting-prep` | Groq-backed pre-meeting summary; `?refresh=true` forces refresh; **cached** in `patient_meeting_prep` with fingerprint invalidation. Response may include **`ai_audit`** (interaction id + governance summary) when audit recording succeeds. |
| `GET` | `/notes/{note_id}` | Full note: transcript, `structured_note`, `entity_payload`, `longitudinal_context`, `embedding_present`. |
| `POST` | `/notes/generate` | **Opt-in** structured note generation + DB insert/update; optional embedding write; gated on `NOTE_GENERATION_ENABLED` and LLM keys. Response may include an **`audit`** block with **`interaction_id`**. |
| `POST` | `/chat` | **Vector RAG** over `notes.embedding`; returns answer + citations and optional **`audit`** metadata. Returns **503** if no embeddings exist for the domain (by design for optional embed step). |
| `GET` | `/admin/responsible-ai/metrics` | **Optional.** Aggregate counts / rolling stats over `ai_interactions` (requires `RESPONSIBLE_AI_ADMIN_ENABLED`; same API key rules as other routes when `BACKEND_API_KEY` is set). |
| `GET` | `/admin/responsible-ai/interactions` | **Optional.** Paginated/filterable list of audit rows. |
| `GET` | `/admin/responsible-ai/interactions/{interaction_id}` | **Optional.** Single interaction detail for Control Center / debugging. |
| `GET` | `/admin/responsible-ai/safety-flags` | **Optional.** Aggregated safety-flag counts from stored governance JSON. |
| `GET` | `/admin/responsible-ai/model-usage` | **Optional.** Model/token/latency aggregates. |

**OpenAPI:** `/docs`, `/redoc`, `/openapi.json` (public when API key middleware is off or for exempt paths).

### 3.5 Supporting modules (non-route)

| Module | Role |
|--------|------|
| `app/db.py` | Request-scoped DB access from pool |
| `app/llm.py` | Groq/Azure chat + JSON structured outputs for note generation |
| `app/embeddings.py` | Query embedding + note embedding helpers for chat / note_generate |
| `app/meeting_prep_service.py` | Meeting prep generation + cache logic |
| `app/schemas/*` | Pydantic models for patients, chat, note generation |
| `app/responsible_ai/*` | Audit logging (including JSONB-safe bindings for `asyncpg`), redaction, hashes, prompt registry, safety heuristics, source trace normalization |
| `app/api/admin_responsible_ai.py` | Admin router for `/admin/responsible-ai/*` (mounted from `main` when the Settings flag is true) |

---

## 4. Frontend (Next.js)

### 4.1 Routes (App Router)

| Path | Description |
|------|-------------|
| `/` | Root entry per `frontend/src/app/page.tsx` |
| `/patients` | **Patients explorer**: sortable table, filter chips, advanced filters, corpus stats; search synced to **`?q=`** on this route. |
| `/patients/[id]` | **Patient chart**: tabs (Read / Sources / Codes & map), meeting prep, timeline + encounter list with **pagination (10)** and **month-bucketed** timeline when visit count is high; generate-note panel. |
| `/patients/[id]/encounters/[encounterId]` | **Encounter viewer** for a single note/encounter. |
| `/chat` | RAG chat UI; optional `?patient_id=` preset; handles backend **503** when embeddings missing. |
| `/docs` | Static Next.js page pointing to in-repo docs (`docs/README.md`, `docs/architecture/README.md`, `docs/roadmap/`, `docs/reference/`). |
| `/admin/responsible-ai` | **Optional.** Responsible AI Control Center (metrics + interaction list) when **`NEXT_PUBLIC_SCRIBE_ADMIN_UI`** is enabled. |
| `/admin/responsible-ai/[interactionId]` | **Optional.** Single interaction detail (matches backend admin GET by id). |

### 4.2 Major components

| Component | Responsibility |
|-----------|----------------|
| `AppShell` | Sidebar (Patients, Chat, Docs, optional **Responsible AI** when admin UI flag is on) on `md+`; mobile menu; sticky **global search** + `ThemeToggle` |
| `GlobalSearchHeader` | Patient search; on `/patients` ties to **`usePatientsListSearchQuery`** / URL `q`; on other routes Enter navigates to patients with query |
| `PatientsExplorer` | List UX: sorting, chips, advanced panel, stats fetch |
| `PatientChartTabs` | Chart tabs, meeting prep, timeline scroll behavior, encounter pagination, codes/sources UI |
| `MeetingPrepPanel` | Fetches meeting prep; refresh; degraded/cached/model display |
| `GenerateNotePanel` | Transcript textarea, specialty/session fields, **postGenerateNote** with backend health + note-generation flags |
| `ThemeToggle` | Dark/light |

### 4.3 API client (`frontend/src/lib/backend.ts`)

Typed helpers: `apiBase`, `fetchBackendHealth`, `fetchCorpusPatientStats`, `fetchPatients`, `fetchPatient`, `fetchMeetingPrep`, `fetchNote`, `postChat`, `postGenerateNote`, optional **`X-API-Key`** / env base URL for demos; when admin UI is on, **Responsible AI** fetchers for metrics, interaction list, and interaction detail.

**Env (frontend):** `NEXT_PUBLIC_SCRIBE_API_BASE`, optional **`NEXT_PUBLIC_SCRIBE_ADMIN_UI`**, optional **`NEXT_PUBLIC_SCRIBE_BACKEND_API_KEY`** if the backend uses `BACKEND_API_KEY`. Documented in **`.env_example`** (repo root) and **`frontend/.env.example`**.

---

## 5. Data pipeline (offline, implemented)

Under **`data_prep/`**: scripted pipeline to build the clinical corpus (patient selection, note matching, adaptation, validation, manifest). Documented in:

- `data_prep/README.md`
- `docs/reference/corpus_offline_pipeline_v2_brief.md`

This is **not** invoked by the FastAPI server at request time; it produces inputs for `load_corpus`.

Corpus builds may emit **generated Markdown** under `data/` (for example `data/clinical_corpus_v2/dataset_card.md`, `audit_report.md`). Treat those files as **build artifacts**, not hand-maintained specs (see **`docs/README.md`**).

---

## 6. Explicitly not in this baseline (planned elsewhere)

Items discussed in roadmaps / agent plans but **not** present as first-class features in the surveyed tree:

- **Audio transcription** service (`POST /transcribe`, Whisper/GCP providers) — see `docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md` §12 and the coding agent plan *Transcription and note generation service*.
- **LangGraph** agent layer for notes (deferred for MVP linear pipeline).
- **Production auth** (SSO, multi-tenant RBAC) beyond optional shared API key.

---

## 7. Related documents

| Document | Use |
|----------|-----|
| `docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md` | UI phases, V2 plan, §12 transcription + note service **planning** |
| `docs/roadmap/SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md` | Responsible AI Control Center product/engineering plan (see **status** at top of that file) |
| `docs/roadmap/PHASE1_MASTER_PLAN.md` | Phase-1 data + app master plan |
| `docs/reference/rag_clinical_note_llm_design.md` | Clinical note / LLM phases |
| `docs/README.md` | Documentation map (roadmaps + references + archives) |
| `docs/archive/README.md` | Superseded long prompts / duplicate guides |

---

## Document history

| Date | Change |
|------|--------|
| 2026-05-04 | Initial **implemented baseline** inventory (repo survey). |
| 2026-05-04 | Added **Functional summary** (end-user flows, platform ops, not-implemented). |
| 2026-05-05 | Documented **Responsible AI Control Center**: `ai_interactions` migration, `app/responsible_ai/`, admin APIs, env flags, frontend admin routes, audit fields on chat/meeting-prep/note generate. |
| 2026-05-06 | Documentation hygiene + **`docs/design/`**: maps/archives; generated-artifact notes; HTML mocks **`docs/design/mockups/`**, screenshots **`docs/design/references/`**; removed **`app docs/`** / **`ui-references/`**; visual artifacts live under **`docs/`** (minimal repo root) |
