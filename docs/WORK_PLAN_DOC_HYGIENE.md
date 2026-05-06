# Work plan: documentation hygiene, truth repair, and evolution trail

**Branch:** `docs/hygiene-pass`  
**Scope:** Documentation and naming only (no application behavior changes in this pass unless a doc fix requires a trivial string in code comments—avoid if possible).  
**Last updated:** 2026-05-05

---

## 1. Goals

1. **Single narrative** for onboarding: what exists, how to run it, where the corpus pipeline lives, where plans live.
2. **Truth repair** where documents contradict the repository layout or the as-built baseline.
3. **Evolution without clutter:** preserve history via **git**, **archives**, and a short **timeline**—not duplicate Markdown trees.
4. **Naming hygiene:** optional **file renames** with clear mapping and a full link sweep so nothing points at dead paths.
5. **Vendor-neutral docs:** repository documentation must not promote or depend on a specific proprietary **AI coding assistant** or its configuration filenames. Use generic language (“local development”, “IDE”, “runbook”).

---

## 2. Policy: vendor-neutral prose vs standard web/API terms

**Feasibility:** High. Tracked Markdown already has **no** references to proprietary assistant products under a narrow search for tooling-style paths and product phrases.

**Clarification (important):** Repository prose should stay **vendor-neutral** (no endorsements of proprietary pair-programming products or their configuration layouts). The following remain acceptable where they are **standard technical artifacts**:

- **CSS:** standard pointer styling and related class names in static HTML mockups under `app docs/` (including the built-in CSS property whose name is the English word for “on-screen pointer shape”).
- **APIs:** opaque **pagination continuation tokens** in REST designs (sometimes exposed as a `limit` plus an opaque string parameter in query strings).
- **UX copy in Markdown:** prefer **“insertion caret”** or **“text caret”** for the blinking insertion indicator so prose does not read like product placement in automated scans.

**Not allowed** in first-party docs (Markdown and non-code doc HTML intended for humans):

- Links or filenames that encode a **vendor assistant** (for example legacy filenames that embed a vendor-specific tool name).
- Instructions that assume a specific commercial **pair-programming tool**, its config directories, or proprietary rules format.

**Broken reference found on disk (not necessarily tracked):** `lakehouse-old/README.md` may still point at a pipeline document path that does not exist under `reference-docs/`. During this pass, if that README is ever committed or distributed, repoint it to the canonical pipeline brief (today: `reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md` or its renamed successor—see §5).

---

## 3. Feasibility assessment

| Item | Feasibility | Notes |
|------|-------------|--------|
| Delete duplicate / stray Markdown (`* copy.md`, duplicate copies under `app docs/`) | **High** | Low risk; update inbound links from roadmaps. |
| Add `docs/README.md` index + `docs/history/` + `docs/archive/` | **High** | Purely additive structure. |
| Fix `lakehouse/` vs `data_prep/` language in PHASE1 and related docs | **Medium** | Large file; prefer **top banner + targeted section edits** over full rewrite. |
| Refresh `SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md` task status vs baseline | **Medium** | Editorial; must align rows with `SCRIBE_IQ_IMPLEMENTED_BASELINE.md`. |
| Reconcile Responsible AI roadmap “implemented” vs checklist | **High** | Replace unchecked boxes with “shipped / link to baseline” + explicit open backlog. |
| Merge or supersede `app docs/SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md` vs `reference-docs/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md` | **Medium–High** | Requires read/compare; outcome is either merge into one spine or archive one with a one-line supersession banner. |
| **Rename** long `SCRIBE_IQ_*` files to shorter, role-based names | **Medium** | **Git mv** preserves history; must run **repo-wide grep** for path updates (README, roadmaps, in-app `/docs` routes if any, `reference-docs/` cross-links). |
| Rename `app docs/` folder (space in path) | **Medium** | Desirable (`design-mockups/` or `ui-mockups/`); touches all links; do in **one dedicated commit** after link inventory. |

**Risk to avoid:** renaming ten files in ten commits without a link matrix—consolidate renames into **one or two PRs** with a checklist.

---

## 4. Execution phases (documentation PRs)

### PR D1 — Quick hygiene

- Remove `app docs/SCRIBE_IQ_DESIGN_PHASE1 copy.md`.
- Add `app docs/README.md` stating: canonical design Markdown lives under `reference-docs/`; this directory retains **HTML mockups** (and temporary MD only if still migrating).
- Remove byte-identical duplicates: `app docs/CLinical_Note_LLM.md`, `app docs/SCRIBE_IQ_DESIGN_PHASE1.md` after fixing all inbound links to `reference-docs/…`.

### PR D2 — Doc tree and archive

- Add `docs/README.md` (map of the documentation set).
- Add `docs/history/EVOLUTION.md` (short timeline: early-phase lakehouse work → canonical `data_prep/`; major shipped areas; link to baseline + key commits or tags when available).
- Add `docs/archive/README.md` (index table: archived file, date, superseded by).
- Move **superseded** long prompts to `docs/archive/` with a short header on each file:
  - `reference-docs/SCRIBE_IQ_DATA_PIPELINE_AGENT.md` (v1 full prompt) → superseded by V2 brief.
  - `reference-docs/SCRIBE_IQ_SIMPLIFIED_IMPLEMENTATION_AGENT.md` → superseded by `SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md` + V2 brief, unless unique content is merged first.

### PR D3 — Truth repair and roadmap consistency

- `roadmap/PHASE1_MASTER_PLAN.md`: banner + correct **active** corpus path (`data_prep/`), clarify **optional local** `lakehouse-old/` vs obsolete `lakehouse/` naming in prose.
- `reference-docs/CLINICAL_LAKEHOUSE_PROPOSAL_V2.md`: banner: historical / architectural; active build is `data_prep/`.
- `reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md`: remove or correct any “`lakehouse/` is the live tree” implication; align with README.
- `roadmap/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md`: refresh task table **or** mark file as historical with pointer to baseline.
- `roadmap/SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md`: reconcile “implemented” with engineering checklist (completed vs open backlog).

### PR D4 — Single implementation spine + link audit

- Resolve duplicate implementation guides (`app docs/SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md` vs `reference-docs/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md`).
- Global link sweep: `grep -r` for old paths after any rename.

### PR D5 (optional) — Controlled renames

**Rename only after D1–D4 stabilize links.** Suggested mapping (adjust after team preference):

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md` | `reference-docs/corpus-build-pipeline-v2.md` | Shorter, role-based; drop redundant prefix |
| `reference-docs/SCRIBE_IQ_IMPLEMENTED_BASELINE.md` | `reference-docs/as-built-baseline.md` | Obvious purpose for new readers |
| `app docs/` | `design-mockups/` or `ui-mockups/` | Removes space; signals content type |

**Rule:** every rename gets a row in `docs/history/EVOLUTION.md` (“Former path → new path, date”).

---

## 5. Data outputs vs specifications

`data/clinical_corpus_v2/audit_report.md` and `dataset_card.md` are **build outputs**, not specifications. Document their role in `docs/README.md` or in the baseline under a short “Generated artifacts” subsection—**do not** merge them into engineering roadmaps.

---

## 6. Confirmation checklist (before merging `docs/hygiene-pass`)

- [ ] `docs/README.md` is the obvious entry from root `README.md`.
- [ ] No first-party Markdown asserts **`lakehouse/`** as the active corpus builder without a historical context label.
- [ ] No duplicate “implementation guide” without a declared supersession line at the top of the archived copy.
- [ ] `docs/archive/README.md` lists all archived files and successors.
- [ ] `docs/history/EVOLUTION.md` explains layout evolution in **under two pages**.
- [ ] Grep audit: no vendor-specific AI assistant setup in docs; standard CSS and pagination terminology only where technically required (see §2).
- [ ] If any file was renamed: all internal links and README pointers updated.

---

## 7. Out of scope for this branch

- Kubernetes, Vercel, or production deployment manifests (separate branch when ready).
- Moving `backend/` / `frontend/` / `data_prep/` directories (separate chore).

---

## Document history

| Date | Change |
|------|--------|
| 2026-05-05 | Initial work plan on branch `docs/hygiene-pass`; incorporates vendor-neutral doc policy, rename feasibility, and phased PRs. |
