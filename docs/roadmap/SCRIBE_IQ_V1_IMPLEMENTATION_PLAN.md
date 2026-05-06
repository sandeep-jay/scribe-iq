---
title: Scribe-IQ V1 Implementation Plan — Chat-first RAG
status: active
last_updated: 2026-05-03
---

# Scribe-IQ V1 Implementation Plan — Chat-first RAG

> **Note (2026-05):** This plan was written as an execution checklist. Task statuses were refreshed against `docs/architecture/IMPLEMENTED_BASELINE.md`. For **current** behavior and flags, treat the baseline as authoritative; this file remains useful for mockup links and original v1 intent.


**Overview:** Postgres + pgvector; **chat-first** v1; **Groq** chat now with **Azure-ready** abstraction; **one transcript per patient** for encounter demo; **longitudinal context** loaded from staged JSONL (**per encounter**) — **no LLM** to rebuild patient summary on page load; **LLM structured note** only on **new transcript** or **explicit regenerate**; **minimal `structured_note` ingest** + embeddings.

**Design references:**

- Backend / RAG: [`docs/reference/Clinical_Note_LLM.md`](../reference/Clinical_Note_LLM.md), [`docs/reference/SCRIBE_IQ_DESIGN_PHASE1.md`](../reference/SCRIBE_IQ_DESIGN_PHASE1.md)
- **UI (mandatory layout reference):** static mockups below — Next.js screens should match **structure, hierarchy, and main copy blocks** unless explicitly revised.

## Task checklist (execution order)

| ID | Task | Status |
|----|------|--------|
| T0 | Env freeze: embedding dim + providers + `backend/.env.example`; canonical paths for corpus/staging | done |
| T1 | `docker-compose.yml` (pgvector) + FastAPI skeleton + `/health` | done |
| T2 | Alembic: patients, notes, external ids, longitudinal JSONB + `embedding vector(1536)` (IVF index deferred) | code done — run locally |
| T3 | Loader + embedding (`scripts.load_corpus`; `--embed` + `OPENAI_API_KEY`) | done (load); embed optional |
| T4 | Read APIs (`GET /patients`, `/patients/{id}`, `/notes/{id}`) — longitudinal via latest note blob | done |
| T5 | `POST /chat` RAG + citations + smoke eval | done (503 until embeddings loaded for domain) |
| T6 | `POST /notes/generate` + guarded persist | done (flag-gated; see baseline) |
| T7 | Frontend: routes + screens per **mockups** (+ `/chat` per Phase1 design) | done |
| T8 | Encounter viewer: transcript + note panels per encounter mockup | done |

---

## UI mockups to routes (**acceptance baseline for T7–T8**)

Implement with **Tailwind + shadcn/ui** (per design docs); **parity target** is these HTML mockups.

| Mockup (`docs/design/mockups/`) | Planned route | Notes |
|----------------------|----------------|------|
| [`scribe_iq_login_page.html`](../design/mockups/scribe_iq_login_page.html) | `/login` | Optional for v1; Phase1 doc had no auth |
| [`scribe_iq_patient_list_professional.html`](../design/mockups/scribe_iq_patient_list_professional.html) | `/` or `/patients` | Stats + table; wire to `GET /patients` |
| [`scribe_iq_patient_detail_final_v2.html`](../design/mockups/scribe_iq_patient_detail_final_v2.html) | `/patients/[id]` | Longitudinal / summary from DB; note list |
| [`scribe_iq_encounter_viewer_professional.html`](../design/mockups/scribe_iq_encounter_viewer_professional.html) | `/patients/[id]/encounter/[encounterId]` | Dialogue + SOAP panes; transcript only where data exists |

**Chat (`/chat`):** required for **chat-first** story; **no HTML mockup in repo**. Use Phase1/simple chat UX; expose entry point from list/detail.

---

## Subtasks — UI (explicit)

- **T7a:** Scaffold `frontend/`; align tokens with mockups.
- **T7b:** Patient list vs [`scribe_iq_patient_list_professional.html`](../design/mockups/scribe_iq_patient_list_professional.html).
- **T7c:** Patient detail vs [`scribe_iq_patient_detail_final_v2.html`](../design/mockups/scribe_iq_patient_detail_final_v2.html).
- **T7d:** Chat vs `POST /chat` (+ citations sidebar).
- **T8a:** Encounter viewer vs [`scribe_iq_encounter_viewer_professional.html`](../design/mockups/scribe_iq_encounter_viewer_professional.html).
- **T8b:** Optional `/login` vs [`scribe_iq_login_page.html`](../design/mockups/scribe_iq_login_page.html).

---

## Locked product decisions

- **Chat-first;** Groq + Azure-shaped config; embeddings fixed **`EMBED_DIM`** (1536 suggested).
- **Longitudinal:** `data/staging/patient_longitudinal_context.jsonl` is **per encounter** — attach by `encounter_id` onto notes rows.
- **LLM summaries** not rebuilt on passive navigation.

---

## Document history

- **2026-05-03:** Filled file (was empty). Added **mandatory mockup-linked** T7/T8 subtasks.
- **2026-05-06:** Refreshed task statuses vs **`docs/architecture/IMPLEMENTED_BASELINE.md`**; design Markdown links → **`docs/reference/`**; mockups/screenshots under **`docs/design/`** (`mockups/`, `references/`); see **`docs/history/EVOLUTION.md`**.
