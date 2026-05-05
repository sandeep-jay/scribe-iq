# Scribe IQ

Clinical documentation / RAG demo — see **`roadmap/PHASE1_MASTER_PLAN.md`**.

## Data pipeline (canonical)

The **50-patient Synthea + note pool + Groq** corpus builder lives in **`data_prep/`**.
Implementation brief: **`reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_CURSOR.md`**.

```bash
cd data_prep
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# … then run scripts 01–09; see data_prep/README.md
```

## Archived: `lakehouse-old/`

Earlier **Project L** staging scripts (AGBonnet, HF classifiers) are preserved under
**`lakehouse-old/`** for reference only. Do not extend them; use **`data_prep/`** for new work.

Architecture notes: **`reference-docs/CLINICAL_LAKEHOUSE_PROPOSAL_V2.md`**.

## Application MVP

After the corpus exists under **`data/clinical_corpus/`**, implement **`backend/`**, **`frontend/`**,
Postgres, and Azure per **`roadmap/PHASE1_MASTER_PLAN.md`**.

## Web app (FastAPI + Next)

- **Patients**: `GET /patients`, `GET /patients/{id}` — list + chart.
- **Pre-meeting summary**: `GET /patients/{id}/meeting-prep` — Groq summary cached in `patient_meeting_prep` until the note fingerprint changes; `?refresh=true` forces regeneration.
- **Corpus stats**: `GET /patients/stats` — total patients + notes for the domain.
- **Note generation**: `POST /notes/generate` — requires `NOTE_GENERATION_ENABLED=true` and `GROQ_API_KEY`.
- **RAG chat** (`POST /chat`) is **deferred until embeddings exist** — needs `OPENAI_API_KEY` and `python -m scripts.load_corpus --embed`. Until then the UI shows a banner; use the patient **Pre-Meeting Summary** for Groq-grounded narrative.
- **Responsible AI:** optional audit trail + **`/admin/responsible-ai`** APIs and Next.js admin UI — see **`reference-docs/SCRIBE_IQ_IMPLEMENTED_BASELINE.md`** and **`roadmap/SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md`**; enable with `RESPONSIBLE_AI_ADMIN_ENABLED` (backend) and `NEXT_PUBLIC_SCRIBE_ADMIN_UI` (frontend).

Run backend: `cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (apply migrations: `alembic upgrade head`).

Run frontend: `cd frontend && npm run dev`.



## Git checkpoints

Before large UI experiments, use a **checkpoint branch** (commands and recorded branch/commit): **`reference-docs/GIT_CHECKPOINTS.md`**.
