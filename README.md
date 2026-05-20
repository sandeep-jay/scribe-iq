**LLM providers:** Demo default is **Groq**. Enterprise: **Azure OpenAI** / **Bedrock**.

# Scribe IQ

Clinical documentation / RAG demo — start with **`docs/README.md`** (full map) · contributor setup in **`docs/guides/README.md`** · deep framing in **`docs/roadmap/PHASE1_MASTER_PLAN.md`**.

## Screenshots

Downsampled PNGs for the README live under **`docs/assets/showcase/readme/`**. Only these showcase exports are versioned in git (full-window captures stay local). The UI is backed by a **synthetic Synthea cohort**—see on-screen labels. A **1200×630** hero crop for social cards is at **`docs/assets/showcase/social/og.png`** (centered on pre-meeting summary + timeline).

### Patient list

![Patient list with cohort stats and filters](docs/assets/showcase/readme/readme-patient-list.png)

### Patient chart

![Patient context, Synthea profile, and chart tabs](docs/assets/showcase/readme/readme-patient-chart.png)

### Pre-meeting summary

![Pre-meeting summary with care timeline](docs/assets/showcase/readme/readme-meeting-prep.png)

### Encounter viewer

![Clinical dialogue alongside structured note](docs/assets/showcase/readme/readme-encounter-viewer.png)

### Responsible AI

![Responsible AI control center](docs/assets/showcase/readme/readme-responsible-ai.png)

## Documentation map

Maintained index: **`docs/README.md`** · architecture hub **`docs/architecture/README.md`**. Short evolution timeline: **`docs/history/EVOLUTION.md`**. Superseded drafts: **`docs/archive/`**.


## Data pipeline (canonical)

The **50-patient Synthea + note pool + Groq** corpus builder lives in **`data_prep/`**.
Implementation brief: **`docs/reference/corpus_offline_pipeline_v2_brief.md`**.

```bash
cd data_prep
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# … then run scripts 01–09; see data_prep/README.md
```

## Archived: `corpus_pipelines/agbonnet_hf_clinical_notes/`

Earlier **Project L** staging scripts (AGBonnet, HF classifiers) are preserved under
**`corpus_pipelines/agbonnet_hf_clinical_notes/`** for reference only. Do not extend them; use **`data_prep/`** for new work.

Architecture notes: **`docs/reference/agbonnet_lakehouse_precursor_proposal_v2.md`**.

## Application MVP

After the corpus exists under **`data/clinical_corpus_v2/`** (see **`data_prep/README.md`** for build outputs and legacy `clinical_corpus_v1/`), implement **`backend/`**, **`frontend/`**,
Postgres, and Azure per **`docs/roadmap/PHASE1_MASTER_PLAN.md`**.

## Web app (FastAPI + Next)

- **Patients**: `GET /patients`, `GET /patients/{id}` — list + chart.
- **Pre-meeting summary**: `GET /patients/{id}/meeting-prep` — Groq summary cached in `patient_meeting_prep` until the note fingerprint changes; `?refresh=true` forces regeneration.
- **Corpus stats**: `GET /patients/stats` — total patients + notes for the domain.
- **Note generation**: `POST /notes/generate` — requires `NOTE_GENERATION_ENABLED=true` and `GROQ_API_KEY`.
- **RAG chat** (`POST /chat`) is **deferred until embeddings exist** — needs `OPENAI_API_KEY` and `python -m scripts.load_corpus --embed`. Until then the UI shows a banner; use the patient **Pre-Meeting Summary** for Groq-grounded narrative.
- **Responsible AI:** optional audit trail + **`/admin/responsible-ai`** APIs and Next.js admin UI — see **`docs/architecture/IMPLEMENTED_BASELINE.md`** and **`docs/roadmap/SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md`**; enable with `RESPONSIBLE_AI_ADMIN_ENABLED` (backend) and `NEXT_PUBLIC_SCRIBE_ADMIN_UI` (frontend).

Run backend: `cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (apply migrations: `alembic upgrade head`).

Run frontend: `cd frontend && npm run dev`.

## Logging quick reference

- **Backend level:** `LOG_LEVEL=INFO` by default; use `LOG_LEVEL=DEBUG` for checkpoint-level events.
- **Frontend level:** `NEXT_PUBLIC_LOG_LEVEL=info` by default; set `debug` for request-start/parse checkpoints.
- **Correlation ID:** frontend sends `X-Request-ID`; backend echoes `x-request-id` and includes request IDs in logs.
- **Safety boundary:** avoid logging PHI/secrets (transcripts, note bodies, API keys). Prefer IDs/counts/status/duration.

## TDD workflow

Use Red -> Green -> Refactor for every feature and bug fix. Start by writing (or updating) a failing test, make the minimum change to pass, then refactor while keeping tests green.

Local pre-push checklist:

- Backend: `cd backend && .venv/bin/tox -e lint,py311`
- Frontend: `cd frontend && npm run lint && npm run test:e2e`
