# Product context

## The problem

Clinical documentation AI has one fundamental reliability problem: language models are fluent liars. They produce confident, well-formatted text that may have no basis in the patient record in front of them. In a clinical setting this is not a usability bug — it is a safety failure.

Scribe IQ is built around a specific answer to this problem: **ground every response in the actual stored record, require citations, and log what the model saw and what it produced.** The architecture reflects that constraint at every layer — retrieval before generation, citations enforced by the prompt contract itself, audit rows on every AI call.

The system is a complete demonstration of those principles on a realistic synthetic patient corpus. It is not a market-ready product, and the documentation does not pretend otherwise. It shows how an offline corpus/data product can become a clinical-shaped AI surface with governance built in from the schema up.

---

## What is built, end to end

One line: **`data_prep/` → generated corpus artifact → Postgres/pgvector → FastAPI → Next.js**, with optional provider-backed narrative generation, optional provider-backed embeddings for RAG chat, and optional Responsible AI admin surfaces.

Layers, without repeating the as-built route list: **data** (`data_prep/` + JSONL), **persistence** (Alembic migrations including `ai_interactions`), **service** (patient/chart/encounter/meeting-prep/chat/note routes), **UI** (App Router), **governance** (append-only interaction rows; admin is optional exposure).

End-user flows, exact routes, and schema: **[`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md)** (Functional summary + HTTP API tables).

---

## Scope boundary

Stated once, plainly:

- **Synthetic data only.** No real patients, no real PHI.
- **Demonstration system, not a production clinical tool.** Not certified, not validated for clinical decision-making.
- **Single-tenant local deployment.** No SSO, no multi-tenant isolation beyond optional API-key auth.
- **English-only.** No multilingual handling or locale awareness.

This boundary is a design choice. Every constraint the system does not solve is a constraint a real product would need to solve, and the architecture is shaped to accept those additions.

---

## What is deferred, and why

These are not gaps — they are decisions about what to demonstrate in this build versus what to leave as well-defined extension points.

| Deferred | Why | Where it plugs in |
|----------|-----|-------------------|
| Audio transcription (`POST /transcribe`) | Adding ASR plumbing dilutes the core demonstration (grounding and governance); transcripts can be pasted into the existing note-generation flow | [`docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md`](../roadmap/SCRIBE_IQ_UI_ROADMAP.md) §12; would precede `POST /notes/generate` |
| Agentic tool loop for chat | The single-shot RAG path is the right baseline to govern first; adding tool loops without an audit story creates more risk than value | `app/api/chat.py` |
| Enterprise SSO and multi-tenant RBAC | Identity is its own design problem; doing it twice (demo identity then real identity) is worse than doing it once when the constraint is real | `OptionalApiKeyMiddleware` is the current gate and the replacement seam |
| LangGraph-style orchestration for notes | The structured-output JSON-mode call is sufficient for the current note shape; orchestration becomes valuable when the note involves real branching | `app/api/note_generate.py` |
| Hosted demo URL and live walkthrough video | Out of scope for this documentation pass; planned as a separate addition | — |

---

## How to evaluate this system

Different audiences look for different things. The documentation is structured to support each.

| You are | Read | What you will learn |
|---------|------|---------------------|
| A product manager or director | This document | Problem, scope, what is deferred and why |
| An architect | [`SYSTEM_OVERVIEW.md`](./SYSTEM_OVERVIEW.md) and [`DESIGN_NOTES.md`](./DESIGN_NOTES.md) | Diagrams, flags, seams; rationale and alternatives |
| An engineer running it | [`docs/guides/QUICKSTART.md`](../guides/QUICKSTART.md) | One supported path to a working UI |
| A reviewer of the as-built | [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md) | Exact routes, schema, env flags |
| A reader of the corpus pipeline | [`data_prep/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data_prep/README.md) and [`docs/reference/corpus_offline_pipeline_v2_brief.md`](../reference/corpus_offline_pipeline_v2_brief.md) | Nine-step pipeline detail |
