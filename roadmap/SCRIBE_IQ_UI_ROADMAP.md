# Scribe IQ — UI roadmap

This document is the **UI / product surface plan** for the web app (Next.js + FastAPI demo). It complements **`roadmap/PHASE1_MASTER_PLAN.md`** (data + backend) and **`reference-docs/GIT_CHECKPOINTS.md`** (git workflow). **No implementation commitments** are implied by ordering; adjust as priorities shift.

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

## Document history

| Date | Change |
|------|--------|
| 2026-05-04 | Initial UI roadmap: phases A–D, principles, out of scope, open decisions. |
| 2026-05-04 | Phase A closed: sidebar + `/docs`, top search/user chrome, patient anchors (see repo history). |
| 2026-05-04 | Phases B–D implemented on branch `feature/ui-roadmap-bcd`: patients findability, chart rail + month timeline, encounter workspace shell. |

