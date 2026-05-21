# Phase 1 Design — RAG Documentation Assistant

> **Archived (2026-05).** Preserved for design lineage. Current authoritative source: [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md). Map: [`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md).


> Focused design for Phase 1 MVP only.
> Local development first. Deployment-ready by design.
> Reference this file when implementing Phase 1 (local MVP).

**Scope:** Phase 1 MVP only. Broader product framing, dual deployments, and cross-phase locked decisions: [`rag_clinical_note_llm_design.md`](rag_clinical_note_llm_design.md). Do not expand Phase 1 scope here without updating that parent design when the change is architectural.

---

## What Phase 1 Delivers

A locally running application where you can:

1. Browse ~50 synthetic patients seeded from a real synthetic clinical dataset
2. Open a patient and see their note history with an AI-generated meeting prep summary
3. Paste a conversation transcript and watch it become a structured clinical note
4. Ask the chatbot questions across the full note corpus and get grounded answers with citations
5. See basic eval numbers proving retrieval works

**That is the complete scope of Phase 1. Nothing else.**

---

## What Phase 1 Does NOT Include

These are explicitly deferred. Do not build them in Phase 1.

- Audio upload or Whisper transcription (Phase 2)
- Hybrid retrieval — structured jsonb search or full-text search (Phase 2)
- LangGraph or any agent framework (Phase 3)
- Graph database (Phase 4)
- Advising domain / second deployment (Phase 5)
- Auth of any kind
- Real-time anything
- PII redaction pipeline
- Multi-tenant support

---

## Local Stack

| Layer | Tool | Notes |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Runs on port 8000 |
| Frontend | Next.js 14 (App Router) | Runs on port 3000 |
| Database | Postgres 16 + pgvector via Docker | Runs on port 5432 |
| Migrations | Alembic | Version-controlled schema |
| DB client | asyncpg | Raw async SQL, no ORM |
| LLM | Azure OpenAI (`gpt-4o-mini`) | Structured outputs via Pydantic |
| Embeddings | Azure OpenAI (`text-embedding-ada-002`) | 1536 dimensions |
| Package mgmt | pip + venv | Classic, macOS |
| UI components | shadcn/ui + Tailwind CSS | No custom design work |

---

## Deployment Readiness (built in from day one)

Phase 1 is local-only but structured so deployment requires only config changes:

- All config via environment variables — no hardcoded values anywhere
- `DATABASE_URL` is the single DB connection point — swap localhost for Supabase
- FastAPI and Next.js are fully decoupled — deploy separately or together
- Alembic migrations run against any Postgres — local Docker or Supabase or Azure DB
- Docker Compose is for local dev only — not used in deployment

When ready to deploy: Vercel for Next.js frontend, Railway or Supabase for Postgres,
Render or Fly.io for FastAPI. No code changes required — only env vars.

---

## Repository Structure

```
rag-docs-assistant/
│
├── DESIGN.md                       ← this file
├── DESIGN_PHASE1.md                ← focused phase 1 design (this file)
├── docker-compose.yml              ← local Postgres only
├── .env.example                    ← template, committed to repo
├── .env                            ← real values, gitignored
├── .gitignore
├── README.md
│
├── backend/                        ← Python / FastAPI
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py               ← settings from env vars
│   │   ├── db.py                   ← asyncpg pool + query helpers
│   │   ├── llm.py                  ← Azure OpenAI wrapper (3 functions only)
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── clinical_note.py    ← Pydantic note + entity models
│   │   │
│   │   ├── domains/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             ← DomainConfig dataclass
│   │   │   └── clinical.py         ← clinical domain config instance
│   │   │
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── generate_note.py    ← transcript → structured note + entities
│   │   │   └── embed.py            ← text → vector + store
│   │   │
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   └── vector.py           ← pgvector similarity search
│   │   │
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── router.py           ← mounts all routers
│   │       ├── patients.py         ← patient endpoints
│   │       ├── notes.py            ← note generation endpoints
│   │       └── chat.py             ← RAG chat endpoint
│   │
│   └── scripts/
│       ├── load_clinical_data.py   ← HuggingFace → DB seed script
│       └── sanity_check.py         ← verify DB is populated + queryable
│
├── frontend/                       ← Next.js app
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── components.json             ← shadcn/ui config
│   │
│   ├── lib/
│   │   └── api.ts                  ← typed API client (calls FastAPI)
│   │
│   ├── types/
│   │   └── index.ts                ← shared TypeScript types
│   │
│   └── app/
│       ├── layout.tsx
│       ├── page.tsx                ← patient list (home)
│       ├── patients/
│       │   └── [id]/
│       │       └── page.tsx        ← patient profile
│       └── chat/
│           └── page.tsx            ← chat interface
│
├── evals/
│   ├── questions.json              ← 20 QA pairs
│   ├── run_eval.py                 ← recall@5 + faithfulness
│   └── results/                    ← gitignored eval outputs
│
└── data/
    └── .gitkeep                    ← HuggingFace cache, gitignored
```

---

## Docker Compose (local dev only)

```yaml
# docker-compose.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: rag_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: rag
      POSTGRES_PASSWORD: rag_dev_password
      POSTGRES_DB: rag_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag -d rag_dev"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

---

## Environment Variables

```bash
# .env.example

# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql://rag:rag_dev_password@localhost:5432/rag_dev

# ── Azure OpenAI ──────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# ── Domain ────────────────────────────────────────────────
DOMAIN=clinical

# ── App ───────────────────────────────────────────────────
# Backend reads these — no defaults, must be set explicitly
LOG_LEVEL=INFO

# ── Frontend (Next.js) ────────────────────────────────────
# Prefix with NEXT_PUBLIC_ to expose to browser
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Database Schema

Single Alembic migration. Run once against local Docker, later against Supabase.

```sql
-- 001_initial_schema.py (expressed as SQL for clarity)

-- ── Extensions ────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Patients ──────────────────────────────────────────────
-- Represents a patient (clinical) or student (advising).
-- "domain" scopes rows per deployment. Phase 1 uses 'clinical' only.
CREATE TABLE patients (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain       TEXT        NOT NULL DEFAULT 'clinical',
    name         TEXT        NOT NULL,    -- synthetic name
    external_id  TEXT,                    -- original dataset reference
    metadata     JSONB       NOT NULL DEFAULT '{}',
    -- clinical: { "specialty": "cardiology", "age": 54, "sex": "M" }
    -- advising: { "major": "CS", "year": "Junior", "gpa": 3.2 }
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON patients (domain);
CREATE INDEX ON patients USING GIN (metadata);

-- ── Notes ─────────────────────────────────────────────────
CREATE TABLE notes (
    id                 UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id         UUID        NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    domain             TEXT        NOT NULL DEFAULT 'clinical',
    conversation_text  TEXT        NOT NULL,   -- raw transcript
    structured_note    JSONB       NOT NULL,   -- LLM-generated structured note
    entity_payload     JSONB       NOT NULL DEFAULT '{}',  -- extracted entities
    embedding          VECTOR(1536),           -- ada-002 embedding of note summary
    specialty          TEXT,                   -- clinical specialty or advising topic
    source             TEXT        NOT NULL DEFAULT 'dataset',  -- 'dataset' | 'uploaded'
    session_date       DATE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON notes (patient_id);
CREATE INDEX ON notes (domain);
CREATE INDEX ON notes (specialty);
CREATE INDEX ON notes USING GIN (entity_payload);

-- Vector index: ivfflat with 100 lists is fine for 500 notes
-- Rebuild with more lists if corpus grows beyond 10k
CREATE INDEX ON notes
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**What goes in `structured_note` (JSONB):**
```json
{
  "chief_complaint": "Patient presents with...",
  "history": "Relevant history includes...",
  "examination": "On examination...",
  "assessment": "Assessment suggests...",
  "plan": "Plan is to...",
  "follow_up": "Follow up in 2 weeks",
  "summary": "2-3 sentence plain-language summary",
  "sentiment": "neutral",
  "topics": ["diabetes management", "medication review"]
}
```

**What goes in `entity_payload` (JSONB):**
```json
{
  "conditions": ["Type 2 Diabetes", "Hypertension"],
  "medications": ["Metformin 500mg", "Lisinopril 10mg"],
  "symptoms": ["fatigue", "polyuria"],
  "procedures": ["HbA1c test"],
  "providers": [],
  "risk_flags": [],
  "follow_up_required": true
}
```

---

## Python Dependencies (`backend/pyproject.toml`)

```toml
[project]
name = "rag-docs-assistant"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # API framework
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",

    # Database
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",   # alembic uses sync driver

    # Azure OpenAI
    "openai>=1.35.0",            # AzureOpenAI client lives here

    # Pydantic
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",

    # Data loading (seed script only)
    "datasets>=2.20.0",
    "tqdm>=4.66.0",

    # Utilities
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",             # async HTTP for eval harness
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",               # linting
]
```

---

## Backend Files

### `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_deployment: str        # gpt-4o-mini
    azure_embedding_deployment: str     # text-embedding-ada-002

    # Domain
    domain: str = "clinical"

    # App
    log_level: str = "INFO"

settings = Settings()
```

### `app/db.py`

```python
import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

# Convenience: fetch a single row, raise if not found
async def fetchrow_or_404(pool: asyncpg.Pool, query: str, *args):
    row = await pool.fetchrow(query, *args)
    if row is None:
        raise ValueError("Not found")
    return row
```

### `app/llm.py`

```python
# Three functions only. All Azure SDK usage lives here.
# Nothing else in the codebase imports from openai directly.

from openai import AsyncAzureOpenAI
from pydantic import BaseModel
from app.config import settings

_client: AsyncAzureOpenAI | None = None

def get_client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    return _client

async def generate_structured(
    messages: list[dict],
    schema: type[BaseModel],
    model: str | None = None,
) -> BaseModel:
    """
    Call Azure OpenAI with structured output.
    Returns a validated Pydantic model instance.
    model defaults to AZURE_OPENAI_DEPLOYMENT (gpt-4o-mini).
    """
    client = get_client()
    response = await client.beta.chat.completions.parse(
        model=model or settings.azure_openai_deployment,
        messages=messages,
        response_format=schema,
    )
    return response.choices[0].message.parsed

async def embed(text: str) -> list[float]:
    """
    Embed text using Azure ada-002.
    Returns a 1536-dimensional float list.
    """
    client = get_client()
    response = await client.embeddings.create(
        model=settings.azure_embedding_deployment,
        input=text[:8000],   # ada-002 token limit buffer
    )
    return response.data[0].embedding

async def transcribe(audio_path: str) -> str:
    """
    Transcribe audio file using Whisper.
    Phase 1: not called anywhere. Ready for Phase 2.
    """
    client = get_client()
    with open(audio_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return response.text
```

### `app/schemas/clinical_note.py`

```python
from pydantic import BaseModel, Field

class ClinicalNote(BaseModel):
    chief_complaint: str = Field(
        description="Primary reason for the visit, 1-2 sentences"
    )
    history: str = Field(
        description="Relevant medical history discussed during the encounter"
    )
    examination: str = Field(
        description="Examination findings or observations noted"
    )
    assessment: str = Field(
        description="Clinical assessment and working diagnosis"
    )
    plan: str = Field(
        description="Treatment plan, prescriptions, referrals, instructions"
    )
    follow_up: str = Field(
        description="Follow-up instructions and timeline"
    )
    summary: str = Field(
        description="2-3 sentence plain-language summary of the full encounter"
    )
    sentiment: str = Field(
        description="Overall tone: one of positive, neutral, negative, mixed"
    )
    topics: list[str] = Field(
        description="3-5 topic tags for this note (e.g. diabetes management, medication review)"
    )

class ClinicalEntityPayload(BaseModel):
    conditions: list[str] = Field(
        default=[],
        description="Medical conditions mentioned or diagnosed"
    )
    medications: list[str] = Field(
        default=[],
        description="Medications mentioned, including dosage if stated"
    )
    symptoms: list[str] = Field(
        default=[],
        description="Symptoms reported by the patient"
    )
    procedures: list[str] = Field(
        default=[],
        description="Procedures, tests, or investigations ordered or discussed"
    )
    providers: list[str] = Field(
        default=[],
        description="Other providers or specialists referenced"
    )
    risk_flags: list[str] = Field(
        default=[],
        description="Any concerns, red flags, or items needing urgent attention"
    )
    follow_up_required: bool = Field(
        default=False,
        description="True if explicit follow-up was scheduled or recommended"
    )

class NoteGenerationOutput(BaseModel):
    """
    Single LLM call produces both note and entity payload.
    Never split across multiple calls during ingestion.
    """
    note: ClinicalNote
    entities: ClinicalEntityPayload
```

### `app/domains/base.py`

```python
from dataclasses import dataclass, field
from pydantic import BaseModel

@dataclass
class DomainConfig:
    name: str                           # display name
    subject_label: str                  # "Patient" | "Student"
    session_label: str                  # "Clinical Encounter" | "Advising Session"
    note_schema: type[BaseModel]
    entity_schema: type[BaseModel]
    output_schema: type[BaseModel]      # combined note + entity for LLM call
    system_prompt: str
    seed_data_path: str
    example_questions: list[str] = field(default_factory=list)
```

### `app/domains/clinical.py`

```python
from app.domains.base import DomainConfig
from app.schemas.clinical_note import ClinicalNote, ClinicalEntityPayload, NoteGenerationOutput

CLINICAL_SYSTEM_PROMPT = """You are a clinical documentation assistant.
Your job is to generate accurate, structured clinical notes from conversation transcripts.

Rules:
- Base the note strictly on what was said in the transcript
- Do not infer or add information not present in the conversation
- Use plain clinical language — avoid unnecessary jargon
- If a section has no relevant content from the transcript, write "Not discussed"
- Extract entities conservatively — only include what was explicitly mentioned
- sentiment should reflect the overall tone of the patient in the conversation
"""

CLINICAL_DOMAIN = DomainConfig(
    name="Clinical Documentation Assistant",
    subject_label="Patient",
    session_label="Clinical Encounter",
    note_schema=ClinicalNote,
    entity_schema=ClinicalEntityPayload,
    output_schema=NoteGenerationOutput,
    system_prompt=CLINICAL_SYSTEM_PROMPT,
    seed_data_path="data/clinical_seed.json",
    example_questions=[
        "Which patients have hypertension and are also on metformin?",
        "Summarize the recent visits for this patient",
        "What are the most common complaints across all patients?",
        "Which patients have a follow-up scheduled?",
        "Are there any patients with risk flags in their recent notes?",
    ],
)
```

### `app/pipeline/generate_note.py`

```python
import json
from app.llm import generate_structured
from app.schemas.clinical_note import NoteGenerationOutput
from app.domains.base import DomainConfig

async def generate_note(
    conversation_text: str,
    domain: DomainConfig,
) -> NoteGenerationOutput:
    """
    Single LLM call: transcript → structured note + entity payload.
    Returns a validated NoteGenerationOutput instance.
    """
    messages = [
        {"role": "system", "content": domain.system_prompt},
        {
            "role": "user",
            "content": f"Generate a structured clinical note from this transcript:\n\n{conversation_text}"
        },
    ]
    return await generate_structured(messages, domain.output_schema)
```

### `app/pipeline/embed.py`

```python
import json
import asyncpg
from app.llm import embed as get_embedding

def note_to_embed_text(structured_note: dict) -> str:
    """
    Concatenate the most semantically rich fields for embedding.
    Summary is highest weight; topics add signal.
    """
    parts = [
        structured_note.get("summary", ""),
        structured_note.get("assessment", ""),
        structured_note.get("plan", ""),
        " ".join(structured_note.get("topics", [])),
    ]
    return " ".join(p for p in parts if p).strip()

async def embed_and_store_note(
    pool: asyncpg.Pool,
    note_id: str,
    structured_note: dict,
) -> None:
    """
    Embed the note's key fields and store the vector in the DB.
    Called after note is already inserted (embedding is nullable on insert).
    """
    text = note_to_embed_text(structured_note)
    vector = await get_embedding(text)

    await pool.execute(
        "UPDATE notes SET embedding = $1 WHERE id = $2",
        vector, note_id
    )
```

### `app/retrieval/vector.py`

```python
import asyncpg
from app.llm import embed

async def vector_search(
    pool: asyncpg.Pool,
    query: str,
    domain: str = "clinical",
    patient_id: str | None = None,
    k: int = 5,
) -> list[dict]:
    """
    Embed the query and return the k most similar notes.
    Optionally scope to a single patient.
    Returns list of dicts with note fields + similarity score.
    """
    query_embedding = await embed(query)

    if patient_id:
        rows = await pool.fetch(
            """
            SELECT
                n.id,
                n.patient_id,
                p.name AS patient_name,
                n.structured_note,
                n.entity_payload,
                n.specialty,
                n.session_date,
                1 - (n.embedding <=> $1::vector) AS score
            FROM notes n
            JOIN patients p ON p.id = n.patient_id
            WHERE n.domain = $2
              AND n.patient_id = $3
              AND n.embedding IS NOT NULL
            ORDER BY n.embedding <=> $1::vector
            LIMIT $4
            """,
            query_embedding, domain, patient_id, k
        )
    else:
        rows = await pool.fetch(
            """
            SELECT
                n.id,
                n.patient_id,
                p.name AS patient_name,
                n.structured_note,
                n.entity_payload,
                n.specialty,
                n.session_date,
                1 - (n.embedding <=> $1::vector) AS score
            FROM notes n
            JOIN patients p ON p.id = n.patient_id
            WHERE n.domain = $2
              AND n.embedding IS NOT NULL
            ORDER BY n.embedding <=> $1::vector
            LIMIT $3
            """,
            query_embedding, domain, k
        )

    return [dict(r) for r in rows]
```

---

## API Endpoints

All endpoints prefixed with `/api/v1`.
FastAPI runs on port 8000.
CORS enabled for `http://localhost:3000`.

```
GET  /health
     → { status: "ok", domain: "clinical", note_count: 412 }

GET  /api/v1/patients
     → { patients: [ { id, name, specialty, note_count, last_session_date } ] }
     Query params: ?specialty=cardiology&limit=50&offset=0

GET  /api/v1/patients/{id}
     → { patient: {...}, notes: [ { id, summary, topics, session_date, sentiment } ] }

GET  /api/v1/patients/{id}/meeting-prep
     → { summary: "3-sentence AI-generated prep summary", generated_at: "..." }
     Cached: regenerate only if new notes since last generation

POST /api/v1/notes/generate
     Body: { conversation_text: string, patient_id: string }
     → { note: ClinicalNote, entities: ClinicalEntityPayload, note_id: string }
     Saves to DB and triggers embedding in background

GET  /api/v1/notes/{id}
     → { note: {...}, patient: {...} }

POST /api/v1/chat
     Body: { message: string, history: [ { role, content } ] }
     → {
         answer: string,
         citations: [ { note_id, patient_name, session_date, excerpt } ],
         retrieved_note_ids: string[]
       }

GET  /api/v1/chat/examples
     → { questions: string[] }   ← from domain config
```

### RAG Chat Logic (`app/api/chat.py`)

The full flow for `POST /api/v1/chat`:

```
1. Embed the user's message
2. vector_search(query, domain, k=5)
3. Format retrieved notes as context block
4. Build prompt:
   - System: "Answer based only on the provided notes. 
              If the answer is not in the notes, say so.
              Always cite which note(s) you used."
   - Context block: formatted retrieved notes with IDs
   - Conversation history (last 6 turns max)
   - User message
5. Call generate_structured() with AnswerOutput schema
6. Return answer + citations mapped back to note metadata
```

```python
# Answer schema
class Citation(BaseModel):
    note_id: str
    excerpt: str = Field(description="The specific part of the note that supports this claim")

class AnswerOutput(BaseModel):
    answer: str = Field(description="Answer to the question based strictly on the provided notes")
    citations: list[Citation] = Field(description="Notes used to generate this answer")
    confidence: str = Field(description="One of: high, medium, low, none")
    # none = answer not found in retrieved notes
```

---

## Data Seeding

### Dataset: `AGBonnet/augmented-clinical-notes`

- Source: HuggingFace — freely available, no login required
- Each sample has: `conversation` (transcript), `note` (reference structured note), `summary` (structured patient summary)
- We use `conversation` as input to our pipeline and `note` as ground truth for eval

### `scripts/load_clinical_data.py` — What it does

```
1. Download AGBonnet/augmented-clinical-notes from HuggingFace
   Cache locally to data/ so it doesn't re-download

2. Filter to 4 specialties:
   cardiology, endocrinology, pulmonology, neurology
   (coherent corpus, good entity diversity for demo)

3. Subset to 400 samples total (~100 per specialty)

4. Group into synthetic patients
   - 50 patients total (~8 notes each)
   - Assign synthetic names (Faker library)
   - Assign consistent specialty per patient

5. For each note:
   a. Call generate_note(conversation_text, CLINICAL_DOMAIN)
   b. Insert patient row if new
   c. Insert note row with structured_note + entity_payload
   d. Call embed_and_store_note()
   e. Progress bar via tqdm

6. Print summary:
   Total patients: 50
   Total notes: 400
   Avg notes per patient: 8.0
   Notes with embeddings: 400
   Failed: 0
```

### Cost estimate for seeding

- 400 notes × ~800 tokens each (note generation): ~320K tokens
- At gpt-4o-mini pricing (~$0.15/1M input): ~$0.05
- Embeddings: 400 × ~200 tokens: ~80K tokens at $0.10/1M: ~$0.01
- **Total: under $0.10 for the full seed run**

---

## Frontend Pages

All API calls go through `frontend/lib/api.ts` — a typed client that reads `NEXT_PUBLIC_API_URL`.
No business logic in frontend components. Components fetch data and render.

### Patient List (`/`)

```
Layout:
- Header: "Clinical Documentation Assistant"
- Search/filter bar: filter by specialty
- Grid of PatientCard components

PatientCard shows:
- Patient name
- Specialty badge
- Note count
- Last session date
- Sentiment indicator (colored dot from most recent note)

Click → navigate to /patients/[id]
```

### Patient Profile (`/patients/[id]`)

```
Layout:
- Back button
- Patient header: name, specialty, metadata
- MeetingPrepSummary component (top of page)
  - "Meeting Prep" label
  - 3-sentence AI summary
  - "Regenerate" button
- Note Timeline (reverse chronological)
  - Each note: date, topics, sentiment chip, expandable
  - Expanded: full structured note fields
  - "Paste new transcript" button → opens modal

PasteTranscriptModal:
- Textarea for conversation text
- "Generate Note" button
- Loading state showing "Generating note..."
- Preview of generated note
- "Save to patient record" button
```

### Chat Interface (`/chat`)

```
Layout:
- Sidebar: list of patients (click to scope chat to one patient)
- Main: chat messages
- Input: text box + send button
- Example questions shown when chat is empty (from domain config)

Message rendering:
- User messages: right-aligned
- Assistant messages: left-aligned
- Citations rendered as chips below each answer
  - Click chip → link to note detail
  - Shows: patient name + date
- Confidence indicator on each answer (high/medium/low/none)
```

---

## Eval Harness

### `evals/questions.json` — 20 QA pairs

Mix of single-patient and cross-corpus questions:

```json
[
  {
    "id": "q001",
    "type": "single_patient",
    "question": "What medications is [Patient Name] currently taking?",
    "expected_note_ids": ["<uuid>"],
    "expected_keywords": ["metformin", "lisinopril"]
  },
  {
    "id": "q002",
    "type": "cross_corpus",
    "question": "Which patients have both hypertension and diabetes?",
    "expected_note_ids": ["<uuid1>", "<uuid2>", "<uuid3>"],
    "expected_keywords": ["hypertension", "diabetes"]
  },
  ...
]
```

Note: populate `expected_note_ids` after the seed run, using `sanity_check.py` to inspect the DB.

### `evals/run_eval.py` — Two metrics

**Retrieval Recall@5:** For each question, did the top 5 retrieved notes include all expected note IDs?

**Answer Faithfulness:** For each answer, use a judge LLM call to check:
*"Is this answer fully supported by the provided notes? Answer yes or no with a brief reason."*

Output: `evals/results/{timestamp}.json` + printed summary table.

---

## Build Order for Claude Code

Hand these to Claude Code as separate tasks in this exact sequence.
Do not give the next task until the current one is verified working.

```
Task 1: Project scaffolding
  - docker-compose.yml
  - .env.example
  - .gitignore
  - README.md (placeholder)
  - backend/pyproject.toml

Task 2: Database
  - backend/alembic.ini
  - backend/alembic/env.py
  - backend/alembic/versions/001_initial_schema.py
  → Verify: docker compose up -d && alembic upgrade head

Task 3: Core backend modules
  - backend/app/config.py
  - backend/app/db.py
  - backend/app/llm.py
  → Verify: python -c "from app.llm import embed; import asyncio; print(asyncio.run(embed('test')))"

Task 4: Schemas and domain config
  - backend/app/schemas/clinical_note.py
  - backend/app/domains/base.py
  - backend/app/domains/clinical.py

Task 5: Pipeline
  - backend/app/pipeline/generate_note.py
  - backend/app/pipeline/embed.py

Task 6: Retrieval
  - backend/app/retrieval/vector.py

Task 7: API
  - backend/app/api/router.py
  - backend/app/api/patients.py
  - backend/app/api/notes.py
  - backend/app/api/chat.py
  - backend/app/main.py (FastAPI app, mounts router, CORS, lifespan)
  → Verify: uvicorn app.main:app --reload → hit /health

Task 8: Seed script
  - backend/scripts/load_clinical_data.py
  - backend/scripts/sanity_check.py
  → Verify: python scripts/load_clinical_data.py → 400 notes inserted

Task 9: Frontend scaffold
  - npx create-next-app@latest frontend (TypeScript, Tailwind, App Router)
  - npx shadcn-ui@latest init
  - frontend/lib/api.ts
  - frontend/types/index.ts

Task 10: Frontend pages
  - frontend/app/page.tsx (patient list)
  - frontend/app/patients/[id]/page.tsx (patient profile)
  - frontend/app/chat/page.tsx (chat interface)
  → Verify: npm run dev → browse patients, open profile, send a chat message

Task 11: Eval harness
  - evals/questions.json (populate after seed run)
  - evals/run_eval.py
  → Verify: python evals/run_eval.py → prints recall@5 and faithfulness table
```

---

## Verification Checklist

Before calling Phase 1 done:

- [ ] `docker compose up -d` starts Postgres cleanly
- [ ] `alembic upgrade head` runs without errors
- [ ] `python scripts/load_clinical_data.py` completes with 400 notes, 0 failures
- [ ] `python scripts/sanity_check.py` shows correct counts + sample vector query works
- [ ] `GET /health` returns `{ status: "ok" }`
- [ ] `GET /api/v1/patients` returns 50 patients
- [ ] `GET /api/v1/patients/{id}` returns patient with notes
- [ ] `GET /api/v1/patients/{id}/meeting-prep` returns AI-generated summary
- [ ] `POST /api/v1/notes/generate` returns structured note from a pasted transcript
- [ ] `POST /api/v1/chat` returns grounded answer with citations
- [ ] Frontend: patient list loads at `localhost:3000`
- [ ] Frontend: patient profile shows notes and meeting prep
- [ ] Frontend: chat returns answers with clickable citation chips
- [ ] `python evals/run_eval.py` prints recall@5 and faithfulness scores
- [ ] No hardcoded values anywhere — all config from `.env`
- [ ] `.env` is in `.gitignore` and not committed

---

## What Good Looks Like

After Phase 1 you should be able to:

1. Open the app in a browser at `localhost:3000`
2. See a list of 50 patients with their specialties
3. Click a patient — see their 8 notes in a timeline and a 3-sentence AI prep summary at the top
4. Click "Paste new transcript" — paste any clinical conversation — see it become a structured note with conditions, medications, symptoms extracted
5. Go to `/chat` — ask "which patients have both hypertension and diabetes?" — get a grounded answer naming specific patients with citations to the exact notes
6. Run `python evals/run_eval.py` — see recall@5 above 0.7 and faithfulness above 0.8

If all six work, Phase 1 is done. Move to Phase 2.

---

*Phase 1 design locked. Last updated before build start.*
*Next: Phase 2 Design (Audio Ingestion + Hybrid Retrieval) — written after Phase 1 ships.*
