# Scribe IQ — UI roadmap

This document is the **UI / product surface plan** for the web app (Next.js + FastAPI demo). It complements **`docs/README.md`** (documentation index), **`docs/roadmap/PHASE1_MASTER_PLAN.md`** (data + backend), and **`docs/architecture/IMPLEMENTED_BASELINE.md`** (inventory of what is implemented today). **No implementation commitments** are implied by ordering; adjust as priorities shift.

---

## 1. Goals and personas

| Goal | Notes |
|------|--------|
| **Clinician-first** | Calm chart read path: who is this patient, what happened recently, what did the model surface, where is the note. |
| **Demo / credibility** | Show handling of healthcare-shaped data (Synthea, longitudinal, codes) without pretending to be a full EHR. |
| **Trust** | Provenance (Sources), degraded/offline LLM states, and honest labeling of synthetic vs inferred fields. |

---

## 2. Current baseline (merged on `main`)

Already in place (high level):

- **App shell:** left sidebar (md+) with Patients, Chat, **Docs**; mobile menu + **slim top bar** (patient search placeholder, demo user); theme toggle; main content region.
- **Patients list:** sortable columns, search, corpus stats.
- **Patient chart:** **Read / Sources / Codes & map** tabs; pre-meeting summary; **full** care timeline with **scroll anchored to latest** (right); **encounter list** newest-first with **UI pagination (10)**; medication hints when present; generate-note panel.
- **Encounter viewer:** two-column encounter + context.
- **Backend-driven:** meeting prep with **Groq fallback** when key missing; chat/RAG deferred when embeddings absent.

Use this section as the **line in the sand** for future diffs: roadmap items below are **incremental**, not rewrites, unless explicitly marked.

---

## 3. Design principles (carry forward)

1. **One primary story per screen** — avoid duplicate rails (timeline vs list already differentiated; keep it that way).
2. **Progressive disclosure** — clinical calm by default; **Sources** and **Codes & map** for depth and demo.
3. **Data honesty** — badges for acuity, programs, tasks, insurance only when backed by real fields or clearly labeled **demo**.
4. **Scale** — long histories: **paginate or virtualize lists**; timeline either **full + scroll strategy** or **bucketed** later; never silently drop visits without UI saying so.
5. **Single accent system** — pick one primary brand color for actions/active nav; keep neutrals for chrome (reference mocks mixed green/purple/blue; align before a visual refresh).

---

## 4. Phase A — Shell and discoverability (highest leverage)

**Objective:** The app reads as one product; users always find **note generation** and **chat** after scrolling.

| Item | Description | Depends on |
|------|-------------|------------|
| **A1. Persistent sidebar** | Left rail: logo/brand, **Patients**, **Chat**, optional **Docs** link; collapse on small breakpoints. Top bar can slim to search + user placeholder. | Layout refactor only. |
| **A2. Patient context header** | On `/patients/[id]`: one consolidated strip (name, external id, DOB/sex line, link to chat) + optional **compact** Synthea signals row; push dense demographics behind **“Profile”** expand. | None. |
| **A3. Section cards + anchors** | Wrap Read blocks in consistent **card** pattern; optional **“Jump to: Summary · Timeline · Encounters · Generate note”** in-page anchors or sticky subnav. | None. |
| **A4. Generate note discoverability** | Sticky footer CTA on mobile, or **“Generate note”** link in header strip / jump row so it is never below-the-fold-only on long histories. | None. |

**Exit criteria:** New user reaches **Generate note** or **Chat** without hunting; patient page feels like one column with clear hierarchy.

---

## 5. Phase B — Patients index and findability

**Objective:** List scales toward many patients without becoming a generic table only.

| Item | Description | Depends on |
|------|-------------|------------|
| **B1. Filter chips (UI)** | e.g. “Has longitudinal”, “≥ N encounters”, specialty text filter — **client-side first** using loaded payload. | Optional: extra fields from API later. |
| **B2. Advanced search panel** | Slide-over or drawer: combined name / external id / date range (session_date) — still **client** if payload bounded; **server** if paginated API added. | API decision for large corpora. |
| **B3. Row density** | Avatar placeholder, secondary line (last session, note count), optional acuity **only if** derived from metadata you trust. | Data. |

**Exit criteria:** Power users can narrow the cohort without leaving the page; golden cohort still loads fast.

---

## 6. Phase C — Patient chart depth (optional rail + timeline evolution)

**Objective:** Richer spatial layout without duplicating the encounter list.

| Item | Description | Depends on |
|------|-------------|------------|
| **C1. Recent visits rail** | Narrow right column: last *k* encounters (title + date + link); desktop only or bottom sheet on mobile. | Layout; reuse same `notes` data. |
| **C2. Timeline at scale** | If 100+ nodes hurt perf: **month buckets** on axis, or **virtualized** nodes; keep “latest visible first” invariant. | Perf testing. |
| **C3. Sources ↔ Read cross-link** | Optional “See sources for this summary” control; keep citations honest (visit-level if sentence-level not available). | Copy + API shape. |

**Exit criteria:** Longitudinal story remains visible; list + rail do not triple-count the same content.

---

## 7. Phase D — Encounter workspace (authoring-oriented)

**Objective:** Move toward mockups with **sectioned encounter** (HPI chips, vitals toggles, exam text) when product shifts from **read-only corpus** to **structured capture**.

| Item | Description | Depends on |
|------|-------------|------------|
| **D1. Sectioned layout** | Mirror `structured_note` keys in a predictable order; empty states per section. | Schema stability. |
| **D2. Vitals / chips** | Interactive chips only where values are real or explicitly demo. | Data model. |
| **D3. Save / draft** | If editing is allowed: autosave, conflict handling — **larger** than a UI-only pass. | Backend + auth. |

**Exit criteria:** Deferred until Phase A–C are stable and product direction includes in-app editing.

---

## 8. Explicitly out of scope (near term)

- Full **CCM / care management** workflows, task queues, billing, insurance verification.
- **Multi-patient browser tabs** inside the app (high complexity; low value for demo).
- **“Assigned to me”** and real SSO without identity product work.

Revisit when the corpus and customer segment require operational workflows.

---

## 9. Open decisions (record answers when you lock them)

1. **Brand accent** — single primary color + dark mode rules (document in a one-page style note when chosen).
2. **Patients API pagination** — when total patients or notes per patient exceed comfortable SSR payload size, add `limit`/`cursor` for **GET /patients** and/or **GET /patients/{id}** notes embed.
3. **Citation depth** — sentence-level meeting-prep citations vs visit-level only (honesty vs impressiveness).

---

## 10. Reference visuals

High-fidelity references (patient overview, CCM enrolled view, patients table, advanced search, encounter vitals) are used as **IA inspiration**, not pixel-perfect specs, until a design system is defined (§3.5).

---

## 11. V2 UI Implementation Plan (reference-aligned, data-feasible)

This V2 plan compares current implementation with the attached UI references and gates each upgrade by current API/data support.

### 11.1 Data feasibility assessment (current backend contracts)

**Directly feasible now (no backend schema change):**
- Patients table visual upgrade: row density, avatar treatment, action affordances, token chips that map to existing filters.
- Global + local search UX polish using existing patient fields (`name`, `external_id`, `last_specialty`, `last_session_date`, `note_count`).
- Patient dashboard composition changes using existing payloads from `GET /patients/{id}` (`metadata`, `notes`, `longitudinal_medication_hints`, `latest_longitudinal`).
- Encounter view hierarchy polish using existing `GET /notes/{id}` (`structured_note`, `entity_payload`, `longitudinal_context`).
- Meeting-prep states/copy polish using existing `GET /patients/{id}/meeting-prep` (`degraded`, `cached`, `model`, `generated_at`).

**Partially feasible (UI can mock, but data quality/meaning is weak):**
- “Risk / eligibility / care program / open tasks” dashboard cards can be shown from synthetic metadata, but clinical semantics are not standardized yet.
- “Active medications” can be inferred from longitudinal hints; this is not a medication reconciliation source of truth.
- Advanced filters like insurer/status/reason/room can render UI controls, but most are not first-class indexed fields in `/patients` yet.

**Not truly feasible yet (needs backend/domain expansion):**
- Real task/worklist pipelines (assigned-to-me, due dates, completion state machine).
- Operational encounter-flow fields (room, staff queue position, waiting-time telemetry) as trusted structured data.
- Full interaction timeline/workflow authoring (CRM-like event log with persistence, ownership, audit semantics).

### 11.2 V2 scope (what we implement now)

1. **Patients Explorer parity (reference-inspired header + filters)**
   - Add top tokenized filter bar and keyword/filter popover pattern.
   - Keep URL-backed search as source of truth (`?q=`), avoid duplicate global/local behavior.
   - Preserve current sorting and chips while improving visual hierarchy.

2. **Advanced Search mode (left rail pattern)**
   - Add optional advanced mode with a left filter rail (recent/saved cues + field stack).
   - Wire only to fields we currently have confidence in (`name`, `external_id`, specialty text, date range over `last_session_date`, longitudinal/note-count chips).
   - Clearly label non-backed controls as “demo filter” until backend support exists.

3. **Patient chart V2 composition**
   - Recompose read view into carded dashboard sections (summary strip, clinical center, utility side column).
   - Keep timeline + encounters as canonical clinical history artifacts; do not duplicate conflicting summaries.
   - Maintain current sticky/scroll behavior: stable app rail, scrollable patient content region.

4. **Encounter workspace V2 polish**
   - Strengthen section grouping (HPI, vitals, exam/assessment/plan) from existing structured payloads.
   - Improve specialty/date prominence and source traceability panels without inventing unsupported data fields.

5. **System-level consistency pass**
   - Unify chip/badge styles, action iconography, and spacing density across patients/chart/encounter surfaces.
   - Keep dark-mode and responsive behavior aligned with current shell constraints.

### 11.3 Defer-to-V3 items (backend/data prerequisites)

- True care-management work queues and ownership semantics.
- Rich operational visit-state dashboards (room/staff/wait-time/order pipelines).
- Structured interaction-history persistence beyond current note/longitudinal model.

### 11.4 Acceptance checks for V2

- Route parity: `/patients`, `/patients/[id]`, `/patients/[id]/encounters/[encounterId]` remain functional.
- No regression in global patient search behavior and URL sync.
- UI states explicitly distinguish **supported clinical data** vs **demo/inferred** chips/cards.
- Build/typecheck pass before merge.

---

## 12. Transcription and note generation service (product + backend alignment)

This section mirrors the **agent plan** *Transcription and note generation service* (same repo’s implementation intent: ASR behind FastAPI, transcript in **Generate note** flow, existing LLM note path). It is here so roadmap readers see **UI, data flow, and vendor options** in one place.

### 12.1 Two capabilities, one demo story

| Capability | Role | UI touchpoint |
|------------|------|----------------|
| **Transcription (ASR)** | Audio (or finalized chunks) → **plain transcript** (optional segments, language). | **Generate note** panel: file upload, optional mic **record → stop → transcribe**, optional chunked/streaming-oriented session UX. |
| **Note generation** | **Clinician-edited** transcript + existing encounter/specialty context → structured note via current backend/LLM. | Same panel after edit; errors must read as **note** failures, not ASR failures. |

**Primary story:** short audio (portfolio cap, e.g. **≤ ~5 minutes**) → transcript → **edit** → **generate note** (linear pipeline; LangGraph deferred per `docs/reference/rag_clinical_note_llm_design.md`).

### 12.2 Batch vs streaming-oriented ingestion (both in scope for planning)

- **Batch:** single upload → one transcription job (simplest path for demos).
- **Streaming-oriented:** either **record-stop → one blob** (reuses batch endpoint) or **session + chunks → finalize** on the server under the same duration/byte caps; UI should distinguish **receiving audio**, **transcribing**, and **final text**.

### 12.3 Provider matrix (config-driven)

| Provider | Env-style flag | Batch | True partial streaming | Notes |
|----------|------------------|-------|-------------------------|--------|
| OpenAI Whisper API | `api` (default) | Yes | No (finalize-only) | Fastest integration; good for CI/demo. |
| Local `faster-whisper` | `local` | Yes | No | Optional dependency group; dev/offline. |
| **GCP Speech-to-Text (v2)** | `gcp` | Yes (sync short; async + GCS for longer jobs) | Yes (bidirectional streaming, interim/final) | Optional; use for **live partial** captions and Google-cloud-native stacks. |

**GCP (summary):** service account or ADC (`GOOGLE_APPLICATION_CREDENTIALS` / workload identity), `roles/speech.client`, project + region + model/recognizer config; verify **pricing and quotas** at implementation time (`https://cloud.google.com/speech-to-text/pricing`). Prefer shipping **Whisper batch → GCP batch → GCP streaming** to limit integration risk.

### 12.4 UX and trust requirements

- Show **provider + model** (when known) and elapsed time for ASR; keep **backend health** gating consistent with meeting-prep / LLM patterns.
- **Never conflate** transcription errors with note-generation (LLM) errors—copy and toasts should name the stage (`pipeline_stage`-style clarity).
- **Non-goals (near term):** sub-200 ms word-level captions as a hard requirement without a streaming-native provider; production diarization guarantees (optional later + honest labeling).

### 12.5 Exit criteria (when this slice is “done” for the roadmap)

- Transcript can be produced from **upload** and from **mic stop** without breaking the existing generate-note path.
- Oversize / over-duration audio rejected with clear validation messaging.
- Optional GCP path documented in `backend/.env.example` when implemented; UI unchanged aside from surfaced provider metadata.

---


## 13. Performance improvement plan (frontend + backend + streaming)

This section records the active performance remediation strategy and complements implementation-focused docs by defining measurable latency targets and phased delivery.

### 13.1 Objectives and measurable targets

- Reduce `/patients` and `/patients/[id]` route p95 by **30–50%** in production-like mode.
- Reduce `/chat` retrieval DB segment p95 by **>50%** after index work.
- Keep Responsible AI admin dashboard p95 under **500 ms** for moderate data volume.
- Reduce perceived wait-to-first-content for AI generation features to **<1.5 s** on warm paths using SSE streaming.

### 13.2 Observed bottleneck areas

1. **Frontend delivery/hydration**
   - Heavy read routes use uncached fetch behavior and route-level waterfalls in some pages.
   - Patient detail surfaces include large client-side render/hydration sections.
2. **Backend query/index gaps**
   - Vector retrieval path and patient timeline queries need stronger index coverage as corpus size grows.
   - Admin analytics rely on repeated full/serial aggregates.
3. **Flow orchestration and runtime mode**
   - Chat/prep generation paths accumulate latency from serial steps.
   - Dev mode (`next dev`, `uvicorn --reload`) inflates perceived latency versus production mode.

### 13.3 Phased execution

| Phase | Focus | Core outcomes |
|------|--------|----------------|
| **P0 Baseline** | Measurement harness | Cold/warm route/API timing baselines; profiling checklist in `docs/reference/`. |
| **P1 Frontend fast wins** | Caching + waterfalls | Route-level cache strategy for stable reads; remove serialized fetch chains where possible. |
| **P2 Backend index optimization** | Query plan efficiency | Add/validate vector and composite indexes for chat, patient timeline, and prep/admin filters. |
| **P3 Backend flow optimization** | Latency accumulation | Overlap independent I/O in generation flows; reduce repeated aggregate scans in admin endpoints. |
| **P3b SSE streaming** | Perceived responsiveness | Add SSE generation endpoints for chat, meeting prep, and note generation while preserving non-stream compatibility. |
| **P4 Runtime hardening** | Environment realism | Document production-like perf run modes; validate Docker/Postgres resource and config assumptions. |
| **P5 Guardrails** | Regression prevention | Lightweight perf checks and endpoint timing visibility for ongoing releases. |

### 13.4 SSE streaming scope (agreed)

- **Transport:** Server-Sent Events (SSE).
- **Surfaces:** chat, meeting prep summary generation, note generation.
- **Compatibility:** keep existing non-stream endpoints as fallback.
- **Audit/trust handling:** write one terminal audit record per completed/cancelled stream with explicit status.

### 13.5 Implementation notes and risks

- Introduce a common SSE event envelope (`start`, `token`, `progress`, `done`, `error`) and one frontend parser utility to avoid drift.
- Treat stream disconnects as explicit cancellable states (do not silently mark success).
- Apply index migrations in controlled windows and verify with `EXPLAIN ANALYZE` before/after snapshots.
- Separate baseline measurements for **dev mode** and **production-like mode** to avoid false conclusions.


## Document history

| Date | Change |
|------|--------|
| 2026-05-04 | Initial UI roadmap: phases A–D, principles, out of scope, open decisions. |
| 2026-05-04 | Phase A closed: sidebar + `/docs`, top search/user chrome, patient anchors (see repo history). |
| 2026-05-04 | Phases B–D implemented on branch `feature/ui-roadmap-bcd`: patients findability, chart rail + month timeline, encounter workspace shell. |
| 2026-05-04 | Added **V2 UI Implementation Plan** with data-feasibility gates from current backend contracts and reference-screen comparison. |
| 2026-05-04 | Added **§12 Transcription and note generation service** (ASR + note path, batch/streaming UX, OpenAI / local / GCP matrix, trust/exit criteria). |
| 2026-05-04 | Intro cross-link to **`docs/architecture/IMPLEMENTED_BASELINE.md`** (implemented inventory). |
| 2026-05-05 | Added **§13 Performance improvement plan** with phased latency remediation and SSE streaming scope (chat + prep + note generation). |
| 2026-05-06 | Linked **`docs/README.md`** from introduction as repository-wide documentation map |

