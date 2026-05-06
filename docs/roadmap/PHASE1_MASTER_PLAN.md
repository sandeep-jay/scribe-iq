# Scribe IQ — Master plan (clinical lakehouse + app MVP)

> **Repository snapshot (2026-05):** The **supported offline corpus pipeline for this repository** is **`data_prep/`** (see root `README.md` and `docs/reference/corpus_offline_pipeline_v2_brief.md`). Later sections use **`lakehouse/`** as historical naming for Project L; the archived scripts on disk live under **`corpus_pipelines/agbonnet_hf_clinical_notes/`** ([`corpus_pipelines/agbonnet_hf_clinical_notes/README.md`](../../corpus_pipelines/agbonnet_hf_clinical_notes/README.md)). Treat **`lakehouse/`** paths in prose as **design lineage**, not required repo layout today. Architecture hub: [`docs/architecture/README.md`](../architecture/README.md); map: **`docs/README.md`**; timeline: **`docs/history/EVOLUTION.md`**.


> **Two projects**
>
> | Project | Purpose | Where |
> |--------|---------|--------|
> | **L — Clinical lakehouse (precursor)** | Curated synthetic corpus (AGBonnet-era HF staging + classification precursors). No app server, no Postgres in this track. | Archived scripts: **`corpus_pipelines/agbonnet_hf_clinical_notes/`**; narrative: **`docs/reference/agbonnet_lakehouse_precursor_proposal_v2.md`**; staging historically **`data/staging/`** |
> | **A — Application MVP** | RAG demo app: `backend/`, `frontend/`, Postgres, Azure. | §4–§15 **below** (schema, API, build order) |
>
> **Handoff:** Start production **`backend/`** after **Project L** meets the lakehouse V2 success criteria (**`data/clinical_corpus/`** + audit, see proposal §10). **Interim prototyping** may use **`create_seed_plan.py`** (50×8 JSONL) only with explicit demo scope — migrate to corpus-driven loading when `data/clinical_corpus/` exists.
>
> This document is the **single source of truth** for **Project A** (application). Lakehouse **pipeline work beyond** validate / stage / classify / export is specified in **`docs/reference/agbonnet_lakehouse_precursor_proposal_v2.md`**.

**Foundation (Project L — early milestones):** **`corpus_pipelines/agbonnet_hf_clinical_notes/scripts/`** (legacy prose may say `lakehouse/`) — **validate** HF (§4.3), **stage** Parquet + `manifest.json` (§4.4), **classify** specialties (§4.5), optional **interim** **`create_seed_plan.py`** (§4.6). **No database / Azure OpenAI in these scripts.** Complete **Project L handoff** before main **Project A** implementation (unless prototyping).

---

## 1. How to use this document

- **Implementers:** Deliver **Project L** to the **corpus handoff** in the lakehouse proposal; then execute **Project A** per §6–§15. The steps in §4.3–§4.6 (`lakehouse/`) are the **first** Project L milestones; remaining lakehouse phases are in **`agbonnet_lakehouse_precursor_proposal_v2.md`**. Then follow §6 (layout), §7 (schema), §9 (API), §14 (build order), §15 (verification).
- **Reviewers:** §2–3 state what was evaluated and what is locked; §16 lists residual risks.
- **Changes:** Any change to locked decisions (§3) must update this file first, then code.

---

## 2. Design evaluation summary

### 2.1 What the reference docs did well

| Area | Assessment |
|------|------------|
| Stack | FastAPI + Next.js + Postgres/pgvector + Azure OpenAI is mature and deployable. |
| Ingestion | One LLM call for `NoteGenerationOutput` (note + entities) is correct for cost, latency, and consistency. |
| Phase boundary | Explicit deferrals (no auth, no audio, no hybrid/agent/graph in MVP) reduce scope creep. |
| Config | Env-driven settings and decoupled frontend/backend support local → cloud without structural rewrites. |
| Evals | Retrieval recall + faithfulness judge is the right *shape* for a RAG MVP. |

### 2.2 Conflicts resolved (canonical choice)

| Topic | Conflict | **Canonical Phase 3 (MVP app) choice** |
|-------|----------|------------------------------|
| Repo layout | Root `app/` vs `backend/app/` | **`backend/` + `frontend/`** — clearer deploy boundaries (Railway/Fly vs Vercel). |
| API prefix | Bare paths vs `/api/v1` | **`/api/v1` on all REST resources**; `/health` may stay unversioned for probes. |
| DB: FTS | Master schema included `search_vector` + trigger in MVP | **Omit** `search_vector`, `pg_trgm`, and FTS trigger until a **later hybrid-retrieval phase** (see reference docs). Keeps MVP aligned with “vector-only search.” |
| Azure deployments | Master: separate `gpt-4o` + mini; older docs: mini only | **Phase 3 MVP: one chat completion deployment** — use **`gpt-4o-mini`** for generation, meeting prep, chat answer synthesis, and judge calls. **Embeddings:** `text-embedding-ada-002` (1536-d). Add `gpt-4o` later for planner/reflection only. |
| Filename drift | References to `DESIGN_PHASE1.md` | **This file:** `docs/roadmap/PHASE1_MASTER_PLAN.md`. |
| Corpus vs app | Mixing HF access with DB seeding | **Phase 0** stages Parquet + manifest; **Phases 1–2** add classifications + seed plan; **Phase 3** loader reads `data/staging/`. |

### 2.3 Gaps filled (this document)

| Gap | Resolution |
|-----|------------|
| Meeting prep caching | New table **`patient_meeting_prep`** + rules in §7.2 and §9.4. |
| “Background” embedding | Specified pattern: **FastAPI `asyncio.create_task`** with **logging + note row flag**; see §8. Alternatives noted for production. |
| Eval vs seed mismatch | Seeding uses **LLM-generated** notes; eval ground truth must target **stored content**, not raw HF `note` field. §11.2 defines the rule. |
| IVFFlat / tiny corpus | **Defer** `CREATE INDEX` on `embedding` until **after** seed completes (`lists = 100` ok for hundreds–few thousand rows); or create index with initial data load. Documented in §7.5. |
| Cross-corpus query expectations | Vector-only RAG is **weak** on boolean/compositional filters. **Phase 3 success criteria** adjust recall expectations for “entity intersection” questions; §11.4. |

---

## 3. Locked decisions (Phase 3 application)

| Decision | Choice |
|----------|--------|
| Runtime | Python **3.11+**, Node **18+** (Next 14 App Router). |
| Backend | **FastAPI**, **asyncpg**, **Alembic**, **Pydantic v2**. |
| DB (local) | **Postgres 16** + **pgvector** (`pgvector/pgvector:pg16` Docker image). |
| LLM (chat completion) | **Azure OpenAI** — one deployment, **`gpt-4o-mini`**, structured outputs via `response_format` / `parse`. |
| Embeddings | **Azure OpenAI** — `text-embedding-ada-002`, **1536** dimensions. |
| Transcription | **Not used in Phase 3 MVP** (no `transcribe()` calls from API). Optional stub in `llm.py` acceptable if unused. |
| Auth | **None**. |
| Primary domain | **`clinical`** only (`DOMAIN=clinical`). |
| Retrieval | **pgvector cosine** only (no FTS, no jsonb entity query in Phase 3 MVP chat path). |
| Frontend | **Next.js 14** App Router, **Tailwind**, **shadcn/ui**. |
| API coupling | Browser → **FastAPI only** (`NEXT_PUBLIC_API_URL`). No business logic in Next API routes. |

---

## 4. Program scope

### 4.1 Phase 3 (application) — in scope — must ship

1. Local **Docker Postgres** + Alembic migrations.  
2. Seed **~50 patients**, **~400 notes** from Hugging Face **`AGBonnet/augmented-clinical-notes`** (**§4.3 Task 0** validates schema before locking the loader).  
3. **Generate** structured note + entity payload from **pasted text**; **save** to DB; **embed** and store vector.  
4. **Patient list** (filter by specialty), **patient detail** + note timeline.  
5. **Meeting prep** (AI summary, cache invalidation on new notes).  
6. **Chat** across corpus with **citations** + confidence; **vector retrieval** only.  
7. **Eval harness:** ≥20 questions, **recall@5**, **faithfulness judge**; documented interpretation (§11.4).

### 4.2 Explicitly out of scope

- Audio upload, Whisper, streaming.  
- Hybrid retrieval (FTS, jsonb filters, RRF).  
- LangGraph / agents / tool use beyond single RAG path.  
- Graph DB (Apache AGE / Neo4j).  
- Advising domain, second deployment, auth, multi-tenant, PII redaction pipeline.

### 4.3 Task 0 — Dataset validation (before build)

Before scaffolding ingestion or the database, validate the Hugging Face dataset **`AGBonnet/augmented-clinical-notes`** so loader field names, specialty filters, and eval assumptions match reality.

**Artifact:** `lakehouse/scripts/validate_dataset.py`

**Out of scope for Task 0:** ingestion, DB schema changes, API routes, FastAPI app — **only** read-only inspection.

**Requirements:**

1. Load the dataset with `datasets.load_dataset` (default split/config as appropriate; document in script help if arguments are needed).

2. Print:

   - dataset split names  
   - row counts per split  
   - column names  
   - first **3** records, **truncated** safely (no megabyte dumps)  
   - missing / null counts per column (where applicable)  
   - approximate text length stats (min / max / mean or percentiles) for columns that look like transcript or note bodies  
   - explicit boolean checks for expected names: `conversation`, `note`, `summary`, and any obvious specialty / category field  

3. **Transcript column detection (heuristic):** flag columns whose names match (case-insensitive): `conversation`, `transcript`, `dialogue`, `text` — plus report which column you recommend as the canonical transcript field.

4. **Note column detection (heuristic):** flag columns matching: `note`, `clinical_note`, `summary`, `output` — plus recommend a canonical reference or gold note field if present (for optional offline eval comparison only; Phase 3 still stores **LLM-generated** notes per §11.2).

5. Summarize findings in a short **“Proceed / Blocker”** line (e.g. missing transcript column = blocker).

**How to run (once the script exists):**

```bash
cd lakehouse
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export HF_HOME="$(pwd)/.hf_home"   # optional if ~/.cache is not writable
mkdir -p "$HF_HOME"
python scripts/validate_dataset.py
```

**What to inspect before proceeding:**

| Output area | Action if wrong |
|-------------|-----------------|
| Splits & row counts | Confirm a split has enough rows for ~400-note subset. |
| Column names | Update loader + §11 mapping if names differ from `conversation` / `note` / specialty. |
| Truncated samples | Confirm transcript vs note are not swapped or empty-dominated. |
| Null counts | Drop or filter columns/rows in loader if key fields are mostly null. |
| Text length stats | Adjust token/char guards for LLM + embedding if texts are huge or tiny. |
| Heuristic transcript/note picks | Exactly **one** canonical transcript column for Phase 3; document choice in loader README or §11.1. |
| Specialty / category | If absent, adjust patient `metadata.specialty` strategy (e.g. constant or derived). |

### 4.4 Task 1 — Stage corpus to disk (Phase 0)

After **PROCEED** from Task 0, materialize a **reproducible local bundle** for downstream phases. **No Postgres.**

**Artifact:** `lakehouse/scripts/stage_dataset.py`

**Output (default):**

- `data/staging/<dataset-slug>/` — Parquet file(s) per split (e.g. `train.parquet`)
- `data/staging/manifest.json` — row counts, column list, optional HF `revision`, **canonical column** recommendations, timestamps

**Run:**

```bash
cd lakehouse && source .venv/bin/activate
python scripts/stage_dataset.py
# optional pin:
python scripts/stage_dataset.py --revision <hf-git-sha>
```

Phase 3 **`load_clinical_data.py`** should read **`data/staging/manifest.json`** and Parquet (or re-download with the same revision) — **HF is optional at ingest time** once staged.

Shared field defaults: `lakehouse/scripts/corpus_constants.py`.

---

### 4.5 Phase 1 — Local specialty classification (no Azure, no Postgres)

Classify **all** staged clinical notes into medical specialties using a **local** Hugging Face model **`anaschahid/medical-specialty-classifier`** (`transformers`, batched GPU/MPS/CPU inference) **before** Phase 2 seed planning.

**Artifact:** `lakehouse/scripts/classify_specialties.py`

**Inputs:**

- `data/staging/manifest.json`
- Parquet path recorded in `manifest.splits.*.parquet_relative` (first split)

**Outputs (repo root–relative):**

| File | Purpose |
|------|---------|
| `data/staging/specialty_predictions.jsonl` | Per-row predictions: `source_row_id`, `predicted_specialty`, `confidence`, top-3 `top_labels`, `text_source`, `model` |
| `data/staging/specialty_prediction_summary.json` | `device_used`, counts, `label_distribution`, `average_confidence`, `low_confidence_count`, timing |

**Processing notes:** prefer **`reference_note`** (`note`); fall back to **`conversation`** when needed; tokenizer **`max_length=512`**. **No Azure OpenAI.** **No Postgres.**

**Run:** see `lakehouse/README.md` — e.g. `python lakehouse/scripts/classify_specialties.py --batch-size 32 --device auto` from repo root.

**Gate:** Phase 2 **seed planning** and Phase 3 **loader** may join these predictions on `source_row_id` / corpus `idx` when assigning patient specialty metadata (exact wiring is a Phase 2/3 concern).

---

### 4.6 Phase 2 — Table-specific seed plan (no LLM, no Postgres)

Turn staged Parquet into a **deterministic, app-shaped** bundle: **400** notes, **50** patients, **8** notes each, **synthetic** specialty + demographics + session dates (today this is **independent** of Phase 1 model labels unless you extend the script to consume `specialty_predictions.jsonl`).

**Artifact:** `lakehouse/scripts/create_seed_plan.py`

**Inputs:**

- `data/staging/manifest.json`
- Parquet path recorded in `manifest.splits.*.parquet_relative`

**Outputs (repo root–relative):**

| File | Purpose |
|------|---------|
| `data/staging/phase1_seed_plan.json` | Counts, exclusion tallies, thresholds, `random_seed`, specialty distribution, paths to JSONL (`phase` / `step` document **Phase 2**) |
| `data/staging/patient_assignments.jsonl` | 50 lines — `patient_id` (UUIDv5), display name, specialty, age, sex, per-note `dataset_idx` + `session_date` |
| `data/staging/selected_note_records.jsonl` | 400 lines — full `conversation`, `reference_note`, optional `full_note` / `summary_json`, linkage to `patient_id` |

**Filtering (defaults; CLI overridable):** drop empty / too-short / too-long conversations and reference notes; drop **duplicate** conversations (SHA-256 of normalized text, first wins). **No Azure OpenAI.**

**Run:** see `lakehouse/README.md` — `python scripts/create_seed_plan.py` (optional `--seed`, `--manifest`, `--repo-root`).

**Gate:** Phase 3 `load_clinical_data.py` should prefer reading **`phase1_seed_plan.json`** + JSONL **or** reproduce the same selections using the recorded `random_seed` and thresholds.

---


## 5. High-level architecture

```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│   Next.js ( :3000 )          │     │   FastAPI ( :8000 )           │
│   List │ Profile │ Chat      │────▶│   patients │ notes │ chat     │
│   lib/api.ts → REST          │     │   pipeline │ retrieval │ llm   │
└──────────────────────────────┘     └──────────────┬───────────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │ Postgres + pgvector │
                                         │ patients │ notes    │
                                         │ patient_meeting_prep│
                                         └──────────┬──────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │   Azure OpenAI      │
                                         │   mini + ada-002    │
                                         └─────────────────────┘
```

---

## 6. Canonical repository layout

**Project L** and **Project A** coexist in one repo; **do not** start production **`backend/`** until **Project L** handoff (unless explicitly prototyping with the interim seed plan).

```
scribe-iq/
├── docs/roadmap/
│   └── PHASE1_MASTER_PLAN.md
├── lakehouse/                         ← Project L — tooling (precursor corpus)
│   ├── README.md
│   ├── requirements.txt
│   └── scripts/
│       ├── corpus_constants.py
│       ├── validate_dataset.py      ← §4.3
│       ├── stage_dataset.py         ← §4.4
│       ├── classify_specialties.py  ← §4.5
│       ├── export_staged_parquet_jsonl.py
│       └── create_seed_plan.py      ← §4.6 interim seed
├── docs/reference/
│   └── agbonnet_lakehouse_precursor_proposal_v2.md
├── data/
│   ├── raw/                         ← future: immutable source drops (see lakehouse proposal)
│   ├── staging/                     ← Project L working output today
│   │   ├── manifest.json
│   │   ├── specialty_predictions.jsonl
│   │   ├── specialty_prediction_summary.json
│   │   ├── phase1_seed_plan.json
│   │   ├── patient_assignments.jsonl
│   │   ├── selected_note_records.jsonl
│   │   └── AGBonnet__augmented-clinical-notes/
│   │       └── train.parquet
│   └── clinical_corpus/             ← future: Project L handoff → Project A loader
├── backend/                         ← Project A (create after handoff / prototype)
│   ├── pyproject.toml
│   ├── alembic/
│   └── app/
├── frontend/                        ← Phase 3
├── evals/
└── docker-compose.yml               ← Phase 3
```

---

## 7. Database schema (Phase 3 application)

### 7.1 Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
```

Use **`gen_random_uuid()`** if you prefer pgcrypto over `uuid-ossp`; pick one consistently in Alembic.

### 7.2 Tables

**`patients`**

| Column | Type | Notes |
|--------|------|--------|
| id | UUID | PK |
| domain | TEXT | Default `'clinical'` |
| name | TEXT | Synthetic display name |
| external_id | TEXT | Nullable; HF key if useful |
| metadata | JSONB | e.g. `specialty`, demographics |
| created_at | TIMESTAMPTZ | |

Indexes: `(domain)`, GIN `(metadata)` optional for specialty JSON paths.

**`notes`**

| Column | Type | Notes |
|--------|------|--------|
| id | UUID | PK |
| patient_id | UUID | FK → patients ON DELETE CASCADE |
| domain | TEXT | Default `'clinical'` |
| conversation_text | TEXT | Raw transcript |
| structured_note | JSONB | LLM output (note sub-object fields) |
| entity_payload | JSONB | LLM entities |
| embedding | VECTOR(1536) | Nullable until embed completes |
| specialty | TEXT | Denormalized filter |
| source | TEXT | `'dataset' \| 'uploaded'` |
| session_date | DATE | Nullable |
| embedding_status | TEXT | **Canonical:** `pending` \| `ready` \| `failed` (default `pending`) |
| created_at | TIMESTAMPTZ | |

Indexes: `(patient_id)`, `(domain)`, `(specialty)`, GIN `(entity_payload)`.  
**Vector index:** see §7.5.

**`patient_meeting_prep`** (new — closes design gap)

| Column | Type | Notes |
|--------|------|--------|
| patient_id | UUID | PK, FK → patients ON DELETE CASCADE |
| summary_text | TEXT | 3–5 sentence prep |
| generated_at | TIMESTAMPTZ | |
| based_on_latest_note_at | TIMESTAMPTZ | Max `notes.created_at` included in generation |

**Invalidation rule:** On `POST` that **inserts** a note for `patient_id`, **delete** the row in `patient_meeting_prep` for that patient (or leave stale and compare timestamps — **deleting** is simpler).  
**Regenerate:** If no row or client forces refresh, compute new summary from last *N* notes (recommend **N = 8** or “all notes” if &lt; 20) via one `gpt-4o-mini` call.

### 7.3 Structured note JSON shape (stored in `structured_note`)

Matches Pydantic `ClinicalNote`: `chief_complaint`, `history`, `examination`, `assessment`, `plan`, `follow_up`, `summary`, `sentiment`, `topics[]`.

### 7.4 Entity payload shape

Matches `ClinicalEntityPayload`: `conditions`, `medications`, `symptoms`, `procedures`, `providers`, `risk_flags`, `follow_up_required`.

### 7.5 Vector index strategy

- For **development**, you may **skip** the IVFFLAT index until the corpus is loaded, then:

```sql
CREATE INDEX ON notes
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

- Queries must filter **`embedding IS NOT NULL`** and **`embedding_status = 'ready'`** (or treat NULL as not searchable).

---

## 8. Embedding pipeline & background completion

### 8.1 `note_to_embed_text`

Concatenate semantically dense fields from `structured_note` dict:

- `summary`, `assessment`, `plan`, and space-joined `topics`.

### 8.2 On note creation (HTTP path)

1. Insert `notes` row with `embedding = NULL`, `embedding_status = 'pending'`.  
2. Return response with `note_id` (and optional inline structured bodies).  
3. Schedule: **`asyncio.create_task(embed_note_job(note_id))`** on the FastAPI event loop **from the request handler**.

### 8.3 `embed_note_job` responsibilities

1. Load row; if missing, log and exit.  
2. Try: compute embedding, `UPDATE notes SET embedding = $v, embedding_status = 'ready' WHERE id = $id`.  
3. On failure: `embedding_status = 'failed'`, log exception (and optionally store last error in a small `embedding_error TEXT` column if you add it in migration).

### 8.4 Caveats (acceptable for Phase 3 MVP)

- **Server restart** may drop in-memory tasks — acceptable for local MVP; **re-run** a small `scripts/repair_embeddings.py` (optional MVP follow-up) or re-hit an admin endpoint to retry `failed`/`pending`.  
- **Production** later: use a queue (RQ, Celery, cloud task) — **not** required for Phase 3 local demo.

### 8.5 Seeding

- Loader may **embed inline** (sequential) for simplicity **or** use the same task pattern. **Recommendation:** **inline sequential** in `load_clinical_data.py` for **deterministic** completion; optionally read rows from **`data/staging/*.parquet`**; HTTP path keeps `create_task`.

---

## 9. API specification

Base URL: `http://localhost:8000`  
Prefix: **`/api/v1`** for all resources below except **`GET /health`**.

CORS: allow `http://localhost:3000`.

### 9.1 `GET /health`

Response:

```json
{
  "status": "ok",
  "domain": "clinical",
  "patient_count": 50,
  "note_count": 400,
  "notes_ready_embedded": 398
}
```

### 9.2 `GET /api/v1/patients`

Query: `specialty`, `limit`, `offset`.

Response: `{ "patients": [ { "id", "name", "specialty", "note_count", "last_session_date" } ] }`

### 9.3 `GET /api/v1/patients/{id}`

Response: `{ "patient": {...}, "notes": [ { "id", "summary", "topics", "session_date", "sentiment", "created_at" } ] }`  
(Optional: include `embedding_status` per note for UI debug.)

### 9.4 `GET /api/v1/patients/{id}/meeting-prep`

- If **`patient_meeting_prep`** exists and `based_on_latest_note_at` ≥ latest note `created_at`: return cached.  
- Else: **generate** (LLM on concatenated recent note summaries), **upsert** cache row, return.

Response:

```json
{
  "summary": "...",
  "generated_at": "2026-05-02T12:00:00Z",
  "cached": true
}
```

`POST /api/v1/patients/{id}/meeting-prep/refresh` (optional) — force invalidate + regenerate.

### 9.5 `POST /api/v1/notes/generate`

Body:

```json
{
  "patient_id": "uuid",
  "conversation_text": "..."
}
```

Behavior:

1. Run `generate_note` (single LLM call).  
2. Insert `notes` with `source: "uploaded"`, `embedding_status: "pending"`.  
3. Invalidate meeting prep for `patient_id`.  
4. Schedule embed task.  
5. Return:

```json
{
  "note_id": "uuid",
  "note": { },
  "entities": { },
  "embedding_status": "pending"
}
```

### 9.6 `GET /api/v1/notes/{id}`

Full detail for drill-down from citations.

### 9.7 `POST /api/v1/chat`

Body: `{ "message": string, "history": [ { "role": "user"|"assistant", "content": string } ], "patient_id": string | null }`

Behavior:

1. `embed(message)`.  
2. `vector_search(k=5)`; if `patient_id` set, **scope** to that patient.  
3. Build context block with note IDs and excerpts (`summary` + key fields, truncated).  
4. `generate_structured` → `AnswerOutput` (answer + citations + confidence).

Response:

```json
{
  "answer": "...",
  "citations": [ { "note_id", "patient_name", "session_date", "excerpt" } ],
  "retrieved_note_ids": [ "..." ],
  "confidence": "high"
}
```

### 9.8 `GET /api/v1/chat/examples`

Returns `{ "questions": [...] }` from `CLINICAL_DOMAIN.example_questions`.

### 9.9 Pydantic: `AnswerOutput`

```python
class Citation(BaseModel):
    note_id: str
    excerpt: str = Field(description="Verbatim or minimally edited span from the provided notes that supports the answer")

class AnswerOutput(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: str = Field(description="One of: high, medium, low, none")
```

System instruction must require: **only** use retrieved notes; if insufficient, answer with **none** confidence and explicit “not enough information in the notes.”

---

## 10. LLM, domain, and prompts

- **System prompt** for note generation: keep **conservative extraction** and **“Not discussed”** for empty sections (as in reference `CLINICAL_SYSTEM_PROMPT`).  
- **Meeting prep prompt:** Input = bullet list of recent `summary` + `topics` + dates; output = 3–5 sentences, no new facts.  
- **Chat judge (eval):** `gpt-4o-mini` is acceptable; keep prompt short and binary-ish with reason.

---

## 11. Data seeding & eval alignment

### 11.1 Loader steps (canonical)

0. **Corpus ready:** Prefer loading from **`data/clinical_corpus/`** (Project L complete). **Interim:** `validate_dataset.py` → PROCEED; `stage_dataset.py` → Parquet + `manifest.json`; `classify_specialties.py` → `specialty_predictions.jsonl` + summary; optional `create_seed_plan.py` → seed JSON/JSONL.  
1. **Read seed plan:** load `data/staging/phase1_seed_plan.json`; iterate `patient_assignments.jsonl` and `selected_note_records.jsonl` (or join on `patient_id` / `dataset_idx`). Optionally join **`specialty_predictions.jsonl`** on `source_row_id` / `idx` when you want model-derived specialty metadata. **Do not** re-sample randomly in the loader unless flags match the plan.  
2. **Insert patients:** use `patient_id`, display name, `metadata` (age, sex), `specialty` from assignments.  
3. **For each note record:** `conversation` → `generate_note(...)`; set `session_date`, `specialty` denormalized on `notes` as needed; `source = 'dataset'`; embed inline.  
4. Print counts; failed generations logged and skipped or retried (policy: **retry once**, then skip with count).

### 11.2 Ground truth for evals

- **`expected_note_ids`** in `evals/questions.json` must be filled **after** seeding by **querying the DB** (or a generated manifest JSON from `sanity_check.py`) so IDs match **this** database state.  
- **Keywords** should align with **generated** `structured_note` / `entity_payload` text, **not** the HF gold `note` field unless you explicitly store HF `note` for offline comparison only.

### 11.3 Question mix (recommended)

| Type | Share | Purpose |
|------|-------|---------|
| Single-patient paraphrase | 40% | Tests retrieval within one patient |
| Corpus-wide thematic / “who mentioned X” | 35% | Tests semantic retrieval |
| Compositional / “both A and B” | ≤25% | **Expected** to be harder under vector-only; documents improvement when **hybrid retrieval** ships (post-MVP) |

### 11.4 Phase 3 success criteria (realistic)

| Metric | Target | Interpretation |
|--------|--------|----------------|
| Recall@5 (overall) | **≥ 0.65** | Good for vector-only MVP |
| Recall@5 (single-patient + thematic) | **≥ 0.75** | Core demo quality |
| Recall@5 (hard compositional) | **≥ 0.45** optional | Baseline to beat when hybrid retrieval ships (post-MVP) |
| Faithfulness (judge) | **≥ 0.80** | When retrieval hits, answers should not invent |

If overall recall stalls: **rewrite questions** toward paraphrase retrieval before changing architecture.

---

## 12. Frontend (Phase 3)

- **`/`** — Patient grid/cards; specialty filter; link to profile.  
- **`/patients/[id]`** — Header, **MeetingPrepSummary** (regenerate), note timeline, modal paste → generate → save.  
- **`/chat`** — Optional sidebar patient scope; messages; citation chips linking to `GET /notes/{id}` or profile anchor.

**`frontend/lib/api.ts`:** typed functions for every endpoint; base URL from `NEXT_PUBLIC_API_URL`.

---

## 13. Environment variables (`.env.example`)

```bash
# Database
DATABASE_URL=postgresql://rag:rag_dev_password@localhost:5432/rag_dev

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

DOMAIN=clinical
LOG_LEVEL=INFO

NEXT_PUBLIC_API_URL=http://localhost:8000
```

Use an API version that supports **`chat.completions.parse`** for your SDK; adjust if your subscription pins a different date.

---

## 14. Build order

### Phase 0 — Dataset validation & staging (no `backend/`, no Postgres)

| Step | Deliverable | Verify |
|------|-------------|--------|
| P0a | `lakehouse/` venv + `pip install -r lakehouse/requirements.txt` | `import datasets` succeeds |
| P0b | Task 0 — `lakehouse/scripts/validate_dataset.py` (§4.3) | **VERDICT: PROCEED**; document any mapping tweaks in loader notes |
| P0c | Task 1 — `lakehouse/scripts/stage_dataset.py` (§4.4) | `data/staging/manifest.json` + `*.parquet` exist |

### Phase 1 — Local specialty classification (still `lakehouse/`)

| Step | Deliverable | Verify |
|------|-------------|--------|
| P1 | `lakehouse/scripts/classify_specialties.py` (§4.5) | `specialty_predictions.jsonl` + `specialty_prediction_summary.json` (row count matches staged rows processed) |

### Phase 2 — Seed planning (`lakehouse/`)

| Step | Deliverable | Verify |
|------|-------------|--------|
| P2 | `lakehouse/scripts/create_seed_plan.py` (§4.6) | `phase1_seed_plan.json` + **`patient_assignments.jsonl` (50 lines)** + **`selected_note_records.jsonl` (400 lines)** |

**Gate:** Do not create production **`backend/`** until **Project L** reaches **`data/clinical_corpus/`** + audit per `agbonnet_lakehouse_precursor_proposal_v2.md` §10 **or** you accept **prototype-only** scope using §4.6 seed artifacts.

### Phase 3 — Application implementation

| Step | Deliverable | Verify |
|------|-------------|--------|
| 1 | `docker-compose.yml`, `.env.example`, `backend/pyproject.toml` | `docker compose up -d` |
| 2 | Alembic + `001_initial_schema.py` (incl. `patient_meeting_prep`, `embedding_status`) | `alembic upgrade head` |
| 3 | `config.py`, `db.py`, `llm.py` | `asyncio.run(embed("test"))` works |
| 4 | Schemas + `clinical.py` domain | import check |
| 5 | `generate_note.py`, `embed.py` | unit smoke optional |
| 6 | `vector.py` | SQL query returns rows after seed |
| 7 | API routers + `main.py` | `/health`, REST paths |
| 8 | `load_clinical_data.py` (reads `data/staging/` + manifest), `sanity_check.py` | 400 notes, embeddings ready |
| 9 | Frontend scaffold including `api.ts` | — |
| 10 | Pages: list, profile, chat | E2E manual |
| 11 | `evals/questions.json` + `run_eval.py` | metrics table |

---

## 15. Verification checklist (Phase 3 MVP done)

- [ ] **Phases 0–2:** P0b **PROCEED**; P0c manifest + Parquet; **P1** specialty JSONL + summary; **P2** `phase1_seed_plan.json` + JSONL (50 / 400 lines); thresholds + `random_seed` reviewed.  
- [ ] Docker Postgres healthy; Alembic at head.  
- [ ] Seed completes; **`embedding_status`** all `ready` (or documented exceptions).  
- [ ] IVFFLAT index created post-seed; vector query fast local for 400 rows.  
- [ ] `/api/v1/patients` and detail return expected shape.  
- [ ] Meeting prep caches; **invalidates** on new note; regenerate works.  
- [ ] Paste transcript → note visible; embed becomes `ready`.  
- [ ] Chat returns citations; confidence `none` when context insufficient.  
- [ ] Eval script runs; metrics meet §11.4 or questions revised accordingly.  
- [ ] No secrets in git; config 100% env-driven.

---

## 16. Residual risks & post-MVP handoff

| Risk | Mitigation in Phase 3 MVP |
|------|------------------------|
| HF dataset schema drift | **Task 0** (`validate_dataset.py`) before app build; pin dataset revision in loader if needed. |
| Azure `parse` / deployment mismatch | Smoke test one structured call in Step 3. |
| Lost embed tasks on restart | `sanity_check` lists `pending`/`failed`; optional repair script. |
| Demo “SQL-style” questions fail | Use §11.3 mix; a **later phase** adds hybrid retrieval. |

**Post-MVP preview:** Add `search_vector` + trigger, `structured.py`, `hybrid.py`, Whisper upload, pipeline UI — per reference roadmap docs.

---

## 17. Document history

| Date | Change |
|------|--------|
| 2026-05-02 | Initial master plan: evaluated reference docs, locked Phase 1, filled schema/API/embed/eval gaps. |
| 2026-05-02 | Added **§4.3 Task 0** (HF `validate_dataset.py`), build Step 0, layout + checklist + risk mitigations. |
| 2026-05-02 | **Phase 0 module `lakehouse/`** (rename from `backend/` for prep); **§4.4 staging**; layout split Phase 0 vs Phase 1; **§14** two-phase build order; loader reads `data/staging/`. |
| 2026-05-03 | Historical: seed artifacts initially tracked as Phase 0 **P0d** / **`phase: "0"`**. **Superseded** by program renumbering (seed planning is **Phase 2**; `phase` / `step` in `phase1_seed_plan.json` are now **`"2"` / `"P2-seed"`**) — see newer history row. |
| 2026-05-02 | **Program phases 0–3** — Phase 1 `classify_specialties.py` (§4.5); seed planning is **Phase 2** (§4.6); MVP app is **Phase 3**; Phase 0 ends at staging (P0c). Updated §14 gates + §11.1. |
| 2026-05-03 | **Two-project framing:** **Project L** (`lakehouse/`, `agbonnet_lakehouse_precursor_proposal_v2.md`) vs **Project A** (this doc). Stale **`backend/`** cache directory removed; **`data_prep/`** scripts moved to **`lakehouse/scripts/`** (legacy **`data_prep/README.md`** redirects). |
| 2026-05-03 | Added **`docs/reference/contributing_git_checkpoints.md`** (checkpoint branch workflow + recorded `checkpoint/pre-read-sources-codes-ui` @ `aae2a40`). *(Doc and master-plan §18 later removed.)* |
| 2026-05-06 | Removed **`docs/reference/contributing_git_checkpoints.md`**; use short-lived feature branches and small commits for UI/IA experiments. |

---

*End of master plan (Project L lakehouse + Project A app MVP).*
