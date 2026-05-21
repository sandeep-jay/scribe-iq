# RAG Documentation Assistant — Design Document

> **Archived (2026-05).** Preserved for design lineage. Current authoritative source: [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md). Map: [`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md).


> Internal reference for implementation by the coding agent.
> All decisions locked. Do not deviate without updating this doc first.

**Scope:** Broader RAG / documentation assistant design (clinical and advising deployments, locked decisions across phases). For **Phase 1 MVP only** (local-first, bounded scope), see [`rag_app_phase1_mvp_design.md`](rag_app_phase1_mvp_design.md). When a change applies to both Phase 1 and later work, update **both** documents in the same PR when practical.

---

## Project Overview

A documentation assistant for 1:1 professional conversations (clinical and academic advising).
Ingests audio or text transcripts, generates structured notes, stores them with embeddings,
and provides an agentic chat interface that answers questions grounded in the note corpus.

**Two deployments, one codebase:**
- `clinical-demo.vercel.app` — seeded with synthetic clinical notes (NoteChat / augmented-clinical-notes)
- `advising-demo.vercel.app` — seeded with synthetic academic advising data (Phase 5)

**Target audiences:**
- Healthcare hiring managers — clinical deployment, Azure + HIPAA framing
- Higher ed hiring managers — advising deployment, FERPA framing

---

## Locked Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend language | Python | HuggingFace datasets, Pydantic, eval harness more idiomatic |
| Backend framework | FastAPI | Async-native, integrates with Pydantic, clean REST |
| Frontend framework | Next.js (App Router) | Vercel deploy, shadcn/ui, API routes unused — all logic in FastAPI |
| Frontend/backend coupling | Fully decoupled | Next.js calls FastAPI REST only. No logic in Next.js API routes. Swappable to Vue later. |
| Database (local dev) | Postgres 16 via Docker (`pgvector/pgvector:pg16`) | pgvector preinstalled, fast local iteration |
| Database (deployed) | Supabase free tier | pgvector built in, simple connection string, good for demo traffic |
| Vector extension | pgvector | Stays in Postgres, no separate vector DB, portable to Azure Database for PostgreSQL |
| Migrations | Alembic | Version-controlled schema, works against any Postgres |
| LLM provider | Azure OpenAI | BAA-covered, healthcare-credible, existing deployment |
| LLM (ingestion tasks) | `gpt-4o-mini` | Structured outputs, cheaper, good enough for summarization |
| LLM (agent planner/reflection) | `gpt-4o` | Better reasoning for multi-step agent work (Phase 3) |
| Embeddings | `text-embedding-ada-002` (upgrade to `3-small` later) | Already deployed on Azure |
| Transcription | OpenAI Whisper API (or `whisper.cpp` locally) | File upload only, no real-time streaming |
| Agent orchestration | LangGraph (Phase 3 only) | Not added until a genuine need exists |
| Package management | pip + venv | Classic, macOS |
| UI components | shadcn/ui + Tailwind | Professional defaults, zero custom design |
| Dev OS | macOS | |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                      │
│   Patient List │ Patient Profile │ Chat │ Pipeline Viz       │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST (JSON)
┌───────────────────────────▼─────────────────────────────────┐
│                        FastAPI Backend                       │
│                                                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Subsystem 1    │  │ Subsystem 2  │  │  Subsystem 3   │  │
│  │  Ingestion      │  │  Knowledge   │  │  Agent         │  │
│  │  Pipeline       │  │  Layer       │  │  (Phase 3)     │  │
│  │                 │  │              │  │                │  │
│  │ Audio/Text      │  │ pgvector     │  │ LangGraph      │  │
│  │ → Whisper       │  │ FTS          │  │ Planner        │  │
│  │ → Note Gen      │  │ jsonb filter │  │ Tools          │  │
│  │ → Entity Ext    │  │ (Phase 4:    │  │ Synthesizer    │  │
│  │ → Embed+Store   │  │  Graph)      │  │ Reflection     │  │
│  └─────────────────┘  └──────────────┘  └────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     Postgres + pgvector                      │
│         patients │ notes │ (Phase 4: graph nodes/edges)      │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      Azure OpenAI                            │
│     gpt-4o-mini (ingestion) │ gpt-4o (agent) │ ada-002       │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
rag-docs-assistant/
├── docker-compose.yml
├── pyproject.toml                  # Python deps
├── .env.example
├── .env                            # gitignored
├── .gitignore
├── README.md
├── DESIGN.md                       # this file
│
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
│
├── app/
│   ├── __init__.py
│   ├── config.py                   # env vars, settings
│   ├── db.py                       # asyncpg pool, query helpers
│   ├── llm.py                      # thin Azure OpenAI wrapper (3 functions)
│   │
│   ├── domains/
│   │   ├── __init__.py
│   │   ├── base.py                 # DomainConfig dataclass
│   │   └── clinical.py             # clinical domain config instance
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── clinical_note.py        # Pydantic note + entity schemas
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── transcribe.py           # Whisper (Phase 2)
│   │   ├── generate_note.py        # transcript → structured note
│   │   └── embed.py                # text → vector
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector.py               # pgvector similarity search
│   │   ├── structured.py           # jsonb + FTS search (Phase 2)
│   │   └── hybrid.py               # RRF merger (Phase 2)
│   │
│   ├── agent/                      # Phase 3 only
│   │   ├── __init__.py
│   │   ├── graph.py                # LangGraph definition
│   │   ├── state.py                # agent state schema
│   │   └── tools/
│   │       ├── meeting_prep.py
│   │       ├── search_notes.py
│   │       ├── compare_subjects.py
│   │       ├── aggregate_themes.py
│   │       ├── draft_followup.py
│   │       └── flag_concerns.py
│   │
│   └── api/
│       ├── __init__.py
│       ├── patients.py             # GET /patients, GET /patients/{id}
│       ├── notes.py                # POST /notes/generate, GET /notes/{id}
│       └── chat.py                 # POST /chat
│
├── scripts/
│   ├── load_clinical_data.py       # HuggingFace → DB
│   └── sanity_check.py             # verify DB populated + queryable
│
├── evals/
│   ├── questions.json              # 20 QA pairs
│   ├── run_eval.py                 # retrieval recall + faithfulness
│   └── results/                    # eval outputs per run
│
├── frontend/                       # Next.js app
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx                # patient list
│   │   ├── patients/[id]/page.tsx  # patient profile
│   │   ├── chat/page.tsx           # chat interface
│   │   └── pipeline/page.tsx       # pipeline viz (Phase 2)
│   └── components/
│       ├── PatientCard.tsx
│       ├── NoteTimeline.tsx
│       ├── MeetingPrepSummary.tsx
│       ├── ChatInterface.tsx
│       └── CitationLink.tsx
│
└── data/
    └── .gitkeep                    # HuggingFace cache lands here
```

---

## Database Schema

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for FTS

-- Patients / subjects table
-- "patient" in clinical, "student" in advising
-- domain_id scopes data per deployment
CREATE TABLE patients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain      TEXT NOT NULL DEFAULT 'clinical',   -- 'clinical' | 'advising'
    external_id TEXT,                                -- original dataset ID if any
    name        TEXT NOT NULL,                       -- synthetic name
    metadata    JSONB NOT NULL DEFAULT '{}',         -- specialty, year, major etc.
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Notes table
CREATE TABLE notes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    domain              TEXT NOT NULL DEFAULT 'clinical',
    conversation_text   TEXT NOT NULL,               -- raw transcript
    structured_note     JSONB NOT NULL,              -- LLM-generated structured note
    entity_payload      JSONB NOT NULL DEFAULT '{}', -- extracted entities for structured retrieval
    embedding           VECTOR(1536),                -- ada-002 / text-embedding-3-small
    search_vector       TSVECTOR,                    -- for full-text search
    source              TEXT NOT NULL DEFAULT 'dataset', -- 'dataset' | 'uploaded'
    specialty           TEXT,                        -- clinical specialty or advising topic
    session_date        DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX ON notes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON notes USING GIN (entity_payload);
CREATE INDEX ON notes USING GIN (search_vector);
CREATE INDEX ON notes (patient_id);
CREATE INDEX ON notes (domain);
CREATE INDEX ON notes (specialty);

-- Auto-update search_vector from conversation_text + structured_note
CREATE OR REPLACE FUNCTION notes_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.conversation_text, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.structured_note::text, '')), 'A');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notes_search_vector_trigger
    BEFORE INSERT OR UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION notes_search_vector_update();
```

---

## Pydantic Schemas

### Clinical Note Schema

```python
from pydantic import BaseModel, Field
from typing import Optional

class ClinicalNote(BaseModel):
    chief_complaint: str = Field(description="Primary reason for the visit in 1-2 sentences")
    history: str = Field(description="Relevant patient history discussed")
    examination: str = Field(description="Examination findings or observations noted")
    assessment: str = Field(description="Clinical assessment and diagnosis")
    plan: str = Field(description="Treatment plan and next steps")
    follow_up: str = Field(description="Follow-up instructions and timeline")
    summary: str = Field(description="2-3 sentence plain-language summary of the encounter")
    sentiment: str = Field(description="One of: positive, neutral, negative, mixed")
    topics: list[str] = Field(description="List of 3-5 topic tags for this note")

class ClinicalEntityPayload(BaseModel):
    conditions: list[str] = Field(default=[], description="Medical conditions mentioned")
    medications: list[str] = Field(default=[], description="Medications mentioned")
    symptoms: list[str] = Field(default=[], description="Symptoms reported")
    procedures: list[str] = Field(default=[], description="Procedures or tests mentioned")
    providers: list[str] = Field(default=[], description="Other providers referenced")
    risk_flags: list[str] = Field(default=[], description="Any risk flags or concerns raised")
    follow_up_required: bool = Field(default=False)

class NoteGenerationOutput(BaseModel):
    note: ClinicalNote
    entities: ClinicalEntityPayload
```

### Advising Note Schema (Phase 5)

```python
class AdvisingNote(BaseModel):
    presenting_concern: str
    academic_history: str
    goals_discussed: str
    action_items: list[str]
    resources_provided: list[str]
    follow_up: str
    summary: str
    sentiment: str
    topics: list[str]

class AdvisingEntityPayload(BaseModel):
    courses: list[str] = Field(default=[])
    majors: list[str] = Field(default=[])
    concerns: list[str] = Field(default=[])
    interventions: list[str] = Field(default=[])
    advisors: list[str] = Field(default=[])
    risk_flags: list[str] = Field(default=[])
    follow_up_required: bool = Field(default=False)
```

---

## Domain Config Pattern

```python
# app/domains/base.py
from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class DomainConfig:
    name: str
    subject_label: str          # "Patient" | "Student"
    session_label: str          # "Clinical Encounter" | "Advising Session"
    note_schema: type[BaseModel]
    entity_schema: type[BaseModel]
    system_prompt: str
    seed_data_path: str
    specialty_field: str        # metadata key used for filtering
    example_questions: list[str]

# app/domains/clinical.py
from app.domains.base import DomainConfig
from app.schemas.clinical_note import ClinicalNote, ClinicalEntityPayload

CLINICAL_DOMAIN = DomainConfig(
    name="Clinical Documentation Assistant",
    subject_label="Patient",
    session_label="Clinical Encounter",
    note_schema=ClinicalNote,
    entity_schema=ClinicalEntityPayload,
    system_prompt=CLINICAL_SYSTEM_PROMPT,   # defined in same file
    seed_data_path="data/clinical_seed.json",
    specialty_field="specialty",
    example_questions=[
        "Which patients have hypertension and are on metformin?",
        "Summarize patient 47's recent visits",
        "What are the most common complaints this month?",
        "Which patients need urgent follow-up?",
        "Compare treatment plans for patients with Type 2 Diabetes",
    ]
)
```

Active domain is selected at startup via `DOMAIN=clinical` env var.

---

## LLM Wrapper (`app/llm.py`)

Three functions. That is all. All Azure-specific code lives here. Nothing else in the codebase touches the SDK directly.

```python
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

client = AsyncAzureOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    api_key=settings.AZURE_OPENAI_API_KEY,
    api_version=settings.AZURE_OPENAI_API_VERSION,
)

async def generate_structured(
    messages: list[dict],
    schema: type[BaseModel],
    model: str = settings.AZURE_OPENAI_MINI_DEPLOYMENT,  # gpt-4o-mini
) -> BaseModel:
    response = await client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=schema,
    )
    return response.choices[0].message.parsed

async def embed(text: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.AZURE_EMBEDDING_DEPLOYMENT,  # text-embedding-ada-002
        input=text,
    )
    return response.data[0].embedding

async def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return response.text
```

---

## API Endpoints

### FastAPI backend (port 8000)

```
GET  /health                        → { status: "ok", domain: "clinical" }

GET  /patients                      → list of patients with summary stats
GET  /patients/{id}                 → patient detail + note timeline
GET  /patients/{id}/meeting-prep    → cached AI-generated prep summary

POST /notes/generate                → { conversation_text } → structured note (not saved)
POST /notes                         → save a generated note to a patient
GET  /notes/{id}                    → single note detail

POST /chat                          → { message, history[] } → { answer, citations[] }
GET  /chat/examples                 → domain example questions
```

### Next.js frontend (port 3000)

```
/                                   → patient list
/patients/[id]                      → patient profile + meeting prep + note timeline
/chat                               → chat interface
/pipeline                           → pipeline visualization (Phase 2)
```

---

## Retrieval Strategy

### Phase 1: Vector only

```python
# Top-k cosine similarity
SELECT id, patient_id, structured_note, conversation_text,
       1 - (embedding <=> $1::vector) AS score
FROM notes
WHERE domain = $2
ORDER BY embedding <=> $1::vector
LIMIT $3;
```

### Phase 2: Hybrid (vector + structured + FTS)

Three retrieval functions, merged with Reciprocal Rank Fusion:

```python
async def hybrid_search(query: str, filters: dict, k: int = 5) -> list[Note]:
    embedding = await llm.embed(query)
    
    vector_results   = await vector_search(embedding, filters, k=20)
    structured_results = await structured_search(filters, k=20)   # jsonb queries
    fts_results      = await fts_search(query, filters, k=20)     # tsvector
    
    return reciprocal_rank_fusion([vector_results, structured_results, fts_results], k=k)
```

### Phase 4: + Graph traversal (Apache AGE or Neo4j Aura)

Adds `traverse_graph(start_node, query)` as an agent tool.

---

## Note Generation Pipeline

### Phase 1 (text input only)

```
conversation_text
    → generate_structured(messages, NoteGenerationOutput)  # single LLM call
    → { note: ClinicalNote, entities: ClinicalEntityPayload }
    → embed(note.summary + " " + " ".join(note.topics))
    → INSERT INTO notes
```

One LLM call generates note + entity payload + sentiment + topics together.
Never split across multiple calls during ingestion — cost and latency.

### Phase 2 (audio input added)

```
audio_file
    → transcribe(audio_path)                # Whisper
    → conversation_text
    → [same as above]
```

Pipeline visualization page exposes each stage with timing.

---

## Agent Design (Phase 3)

### LangGraph graph structure

```
user_message
    → [Planner Node]          classify intent, select tools, may run tools in parallel
    → [Executor Nodes]        run selected tools, collect results
    → [Synthesizer Node]      compose answer with inline citations
    → [Reflection Node]       check grounding; if answer ungrounded → back to Planner
    → response
```

### Tools

| Tool | Input | Uses |
|---|---|---|
| `get_meeting_prep` | `patient_id` | Recent notes + structured summary |
| `search_notes` | `query, filters` | Hybrid retrieval (Phase 2) |
| `compare_subjects` | `patient_ids, dimension` | Parallel note retrieval + comparison |
| `aggregate_themes` | `filters` | Cross-corpus pattern detection |
| `draft_followup` | `note_id, tone` | LLM generation from note content |
| `flag_concerns` | `patient_id` | Risk signal detection in recent notes |
| `traverse_graph` | `start_node, query` | Graph traversal (Phase 4) |

### Model routing

- Planner node, Reflection node: `gpt-4o`
- All tool execution and synthesis: `gpt-4o-mini`

---

## Eval Harness

### Structure (`evals/questions.json`)

```json
[
  {
    "id": "q001",
    "question": "What medications is patient 12 currently taking?",
    "expected_note_ids": ["uuid-1", "uuid-3"],
    "expected_answer_contains": ["metformin", "lisinopril"],
    "type": "single_patient"
  },
  {
    "id": "q002",
    "question": "Which patients have reported fatigue as a symptom?",
    "expected_note_ids": ["uuid-5", "uuid-8", "uuid-11"],
    "expected_answer_contains": ["fatigue"],
    "type": "cross_corpus"
  }
]
```

### Metrics

- **Retrieval recall@5** — were the expected note IDs in the top 5 retrieved?
- **Answer faithfulness** — LLM judge checks if the answer is supported by retrieved notes (no hallucination)
- **Schema validity rate** — % of generated notes that pass Pydantic validation (ingestion pipeline)

Results saved to `evals/results/{timestamp}.json` and summarized in README.

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://rag:rag_dev_password@localhost:5432/rag_dev

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o                  # used for agent planner/reflection
AZURE_OPENAI_MINI_DEPLOYMENT=gpt-4o-mini        # used for ingestion pipeline
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Domain
DOMAIN=clinical                                  # 'clinical' | 'advising'

# App
NEXT_PUBLIC_API_URL=http://localhost:8000        # FastAPI base URL
```

---

## Phase Roadmap

### Phase 1 — MVP Foundation
**Outcome:** Live URL. Browse patients, read notes, generate new notes from text, ask chatbot questions, see grounded answers with citations.

Tasks:
- Docker Compose + local Postgres setup
- Alembic migration (schema above)
- `app/llm.py` — three-function Azure wrapper
- `app/domains/clinical.py` — domain config
- `app/schemas/clinical_note.py` — Pydantic schemas
- `scripts/load_clinical_data.py` — HuggingFace loader (300–500 samples, 3–5 specialties, grouped into ~50–60 patients)
- `app/pipeline/generate_note.py` — transcript → structured note
- `app/pipeline/embed.py` — text → vector, store in DB
- `app/retrieval/vector.py` — basic pgvector search
- FastAPI endpoints: patients, notes/generate, chat (vector-only RAG)
- Next.js: patient list, patient profile + meeting prep summary, chat page
- Eval harness v1: 20 QA pairs, recall@5, faithfulness
- Deploy to Vercel + Supabase

**Stop point:** Solid junior-to-mid portfolio piece.

---

### Phase 2 — Audio Ingestion + Hybrid Retrieval
**Outcome:** Subsystem 1 (ingestion) is its own demoable surface. Chatbot answers relational questions.

Tasks:
- `app/pipeline/transcribe.py` — Whisper file upload
- Pipeline visualization page in Next.js (stage timings, metrics)
- `app/retrieval/structured.py` — jsonb + FTS queries
- `app/retrieval/hybrid.py` — RRF merger
- Upgrade `/chat` endpoint to use hybrid retrieval
- Expand eval harness with relational questions, baseline comparison
- README: "Three Retrieval Strategies" section

**Stop point:** Mid-level portfolio piece. Audio pipeline is strong standalone demo asset.

---

### Phase 3 — Agentic Layer (LangGraph)
**Outcome:** Chatbot is visibly reasoning. Trace UI shows tool calls and planner rationale.

Tasks:
- `app/agent/state.py` — agent state schema
- `app/agent/tools/` — six tool implementations
- `app/agent/graph.py` — LangGraph planner/executor/synthesizer/reflection
- Upgrade `/chat` endpoint to use agent
- Agent trace side panel in chat UI
- README: "v1 RAG → v2 Agentic" comparison section

**Stop point:** Senior-flavored. Reflection node signals grounding seriousness for regulated domains.

---

### Phase 4 — Graph Layer
**Outcome:** Three retrieval strategies. Multi-hop questions answerable.

Tasks:
- Graph backend setup (Apache AGE preferred, Neo4j Aura fallback)
- Graph schema (nodes: Patient, Condition, Medication, Symptom, Provider, Visit)
- Conversion script: entity payloads → graph nodes/edges
- `app/agent/tools/traverse_graph.py` — graph traversal tool
- Multi-hop demo questions as example prompts
- Expand eval harness with graph-specific questions
- README: retrieval comparison table (vector / structured / graph)

**Stop point:** Strong for healthcare-specific roles. Knowledge graph reasoning is a credibility marker.

---

### Phase 5 — Second Domain + Polish
**Outcome:** Two live deployments. Full portfolio polish for both audiences.

Tasks:
- Generate ~30 synthetic advising sessions (10 students, persona × scenario × style variance)
- `app/domains/advising.py` + advising Pydantic schemas
- Verify domain switch end-to-end: `DOMAIN=advising`
- Second Vercel deployment
- README rewrite (hero, architecture diagram, retrieval strategies, agent design, eval results, production considerations, decision log)
- Two screen recordings (90s each): healthcare cut + higher ed cut
- Portfolio site / LinkedIn framing

**Stop point:** Full project. Covers 8+ competency dimensions. Both audiences addressed.

---

## Phase Selection Guide

| Stop after | Portfolio level | Best for |
|---|---|---|
| Phase 1 | Working RAG demo | Junior–mid roles, quick portfolio refresh |
| Phase 2 | Hybrid retrieval + audio | Mid-level RAG/ML engineer roles |
| Phase 3 | Agent architecture | Senior-flavored, regulated-domain credibility |
| Phase 4 | Three retrieval strategies | Healthcare-specific or RAG-focused roles |
| Phase 5 | Two domains, full polish | Dual-audience, comprehensive portfolio piece |

**Recommended commitment:** Phase 3 minimum. Decide at Phase 3 boundary whether to continue.

---

## Production Considerations (README section — no build required)

> "Production deployment path: Azure OpenAI Service (BAA-covered) for LLM inference,
> Azure Database for PostgreSQL Flexible Server with pgvector for storage (same VNet as
> inference layer), Azure AI Speech for HIPAA-compliant transcription, Azure Key Vault
> for secrets management, Azure Private Link for endpoint isolation. PHI redaction
> performed before any data reaches the LLM. Architecture is FERPA-aligned for higher
> ed deployments via the advising domain configuration. Real-time transcription would
> use streaming Whisper with partial transcript processing; current implementation uses
> file upload for demo simplicity."

---

## Key Constraints and Risks

- **Embedding model switch requires full re-embed.** If upgrading from ada-002 to text-embedding-3-small, run `scripts/reembed.py` against the full corpus. Cost: <$1 for 500 notes.
- **Supabase pauses after 1 week of inactivity.** Set up a cron ping or accept the 30-second cold start.
- **Apache AGE not supported on Supabase free tier.** Phase 4 graph layer needs local demo or Neo4j Aura free tier as separate graph DB alongside Supabase.
- **LangGraph version churn.** Pin version in `requirements.txt` before Phase 3.
- **gpt-4o-mini availability.** Confirm available in your Azure region before Phase 1. Fallback: gpt-4o (already deployed).
- **HuggingFace dataset size.** Start with 300–500 samples. Re-embedding if schema changes costs <$1.
- **Never put business logic in Next.js API routes.** All logic stays in FastAPI. Frontend is a rendering layer only.

---

*Last updated: Phase 1 pre-build. Update this document when any locked decision changes.*
