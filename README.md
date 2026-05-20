**LLM providers:** Demo default is **Groq**. Enterprise: **Azure OpenAI** / **Bedrock**.

# Scribe IQ

Scribe IQ is a full-stack clinical documentation and retrieval system built on a synthetic patient corpus. It demonstrates three things end-to-end: grounding LLM responses in a structured record so answers are citation-backed, generating structured clinical notes from transcripts, and making every AI interaction auditable from day one — not as a feature added later, but as a constraint woven into the architecture.

Built on synthetic data. Not for clinical decision-making.

The system has been built incrementally; the documentation is maintained alongside it. The index below is the canonical entry point.

---

## Where to go next

| If you want to | Open |
|----------------|------|
| Understand the architecture (diagrams, flags, seams) | [`docs/overview/SYSTEM_OVERVIEW.md`](docs/overview/SYSTEM_OVERVIEW.md) |
| Understand the product framing and scope | [`docs/overview/PRODUCT_CONTEXT.md`](docs/overview/PRODUCT_CONTEXT.md) |
| Run the system locally | [`docs/guides/QUICKSTART.md`](docs/guides/QUICKSTART.md) |
| Read rationale and alternatives considered | [`docs/overview/DESIGN_NOTES.md`](docs/overview/DESIGN_NOTES.md) |
| Inspect the as-built API and schema | [`docs/architecture/IMPLEMENTED_BASELINE.md`](docs/architecture/IMPLEMENTED_BASELINE.md) |
| See the full documentation map | [`docs/README.md`](docs/README.md) |

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (App Router), TypeScript |
| Backend | FastAPI, asyncpg, Pydantic |
| Data store | Postgres 16 with pgvector |
| LLM | Groq (OpenAI-compatible API) |
| Embeddings | OpenAI (optional) |
| Migrations | Alembic |
| Corpus pipeline | Python, Synthea, Hugging Face datasets, Groq |

---

## What each key unlocks

Every external dependency is optional. The system degrades gracefully and reports what is configured via `GET /health`.

| Without any keys | `GROQ_API_KEY` | `OPENAI_API_KEY` + `--embed` | Admin flags |
|------------------|----------------|------------------------------|-------------|
| Patient list, charts, encounter viewer | Pre-meeting summaries, structured note generation | RAG chat with citations | Responsible AI Control Center |

For the full flag matrix, see [`docs/overview/SYSTEM_OVERVIEW.md`](docs/overview/SYSTEM_OVERVIEW.md#capability-flags).

---

## Screenshots

The UI is backed by a synthetic Synthea cohort; on-screen labels make this explicit.

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

---

## Architecture themes (short)

**Vectors in Postgres** · **Retrieval-first chat with citation syntax** · **Append-only `ai_interactions` on AI routes**. Diagrams, flags, and extension table: [`docs/overview/SYSTEM_OVERVIEW.md`](docs/overview/SYSTEM_OVERVIEW.md). Rationale and alternatives: [`docs/overview/DESIGN_NOTES.md`](docs/overview/DESIGN_NOTES.md).

---

## Quick start

The pre-built corpus under `data/clinical_corpus_v2/` is loaded into Postgres in one command. Full prerequisites, optional capability paths, and troubleshooting: [`docs/guides/QUICKSTART.md`](docs/guides/QUICKSTART.md).

```bash
docker compose up -d
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e .
alembic upgrade head
scribe-load-corpus
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# in a second terminal
cd frontend && nvm use && npm install && npm run dev
```

Frontend: <http://localhost:3000>. Backend: <http://127.0.0.1:8000/health>.
