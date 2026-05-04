# Adapt notes: finalized design (longitudinal context + demo)

This document fixes the **target design** for clinical note adaptation (`06_adapt_notes.py`) and the **longitudinal context** stage that feeds it. It reflects the current repo reality: **`match_results.jsonl`** fuses **Synthea-grounded structured encounter fields** with **external reference prose** (`best_note_text` from sources such as MedSynth / MT Samples), plus optional **ACI-Bench** for showcase visits.

---

## 1. Goals

- **Continuity**: Notes for visit *t* reflect **prior visits** (recent chart memory), not an isolated rewrite.
- **Grounding**: Prior memory is **mostly structured** (from `match_results` / Synthea-linked fields). Optional short narrative summaries **derive only from that structured window**, not from prior LLM outputs.
- **Auditability**: Persist **what context** was used for each adapted row (for QC, reproducibility, demos).
- **Template fidelity (today only)**: The **reference note** that shapes section structure remains **today’s** `best_note_text` (capped), not a stack of three full prior templates.

Non-goals for v1: perfect clinical fidelity; using full prior adapted notes as the primary memory; summarizing prior reference prose at full length.

---

## 2. Pipeline (target)

| Stage | Artifact | Responsibility |
|--------|-----------|----------------|
| Existing | `match_results.jsonl` | Per-encounter structured fields + `best_note_*` match |
| Existing | `selected_patients*.jsonl` | Cohort filter |
| **New** | `patient_longitudinal_context.jsonl` | **Deterministic** prior-window + rollup **per (`patient_id`, `encounter_id`)** |
| Optional | LLM micro-summary | 2–6 sentences from structured window only; versioned |
| Existing (extended) | `06_adapt_notes.py` | Single Groq call: **PRIOR CONTEXT + TODAY + REFERENCE NOTE (today)** |
| Existing | `07_assemble_corpus.py` | Corpus assembly; should read per-note provenance if present |

**Order:** Build **longitudinal context before** adaptation for each encounter (chrono per patient). Do **not** primary-rollup from prior **adapted** notes.

---

## 3. Longitudinal context (v1 rules)

### 3.1 Window

- For encounter *t*, take the **K = 3** most recent **prior** rows with `encounter_date < t` (configurable via env, e.g. `SCRIBE_PRIOR_VISITS=3`).
- Fewer than three exist at early visits: use **1 or 2**.
- Sort order: `encounter_date`, tie-break `encounter_id`.

### 3.2 Per prior visit block (structured)

For each prior *p*, include (with **caps** on list length and string length):

- `encounter_date`, `encounter_id`
- `encounter_reason` or explicit **not documented**
- `conditions` (capped)
- `medications` (capped)
- `recent_obs` (capped; same style as `format_obs` in `06`)

Optional: `match_score`, `best_note_source` for audit only.

### 3.3 Optional deterministic rollup

Single block, e.g.:

- Union / top-N of recurring conditions across the window
- Recent nonempty reasons (deduped tail)
- New since last visit via set diff on conditions (best-effort)

### 3.4 Optional LLM summary (v1.1)

- Input: **only** structured window + deterministic rollup text.
- Output: short clinical English; store `prior_summary_model`, `prior_summary_prompt_version`.
- Still persist structured window **verbatim** regardless.

### 3.5 Schema versioning

- Every context row carries `context_schema_version` (e.g. `1.0`).

---

## 4. Adapt notes (`06`) — prompt contract

### 4.1 Sections (conceptual)

1. **PRIOR VISITS (last K)** — blocks from longitudinal context (structured; optional short summary).
2. **TODAY’S PATIENT / ENCOUNTER** — existing fields: age, sex, visit date, reason, conditions, medications, observations (today’s row).
3. **REFERENCE NOTE (today only)** — `best_note_text[:N]` for **current** encounter only.
4. **Instructions** — e.g. reflect **today** vs priors (stable / improving / worsening / unknown); do not recycle a prior chief complaint if today’s reason conflicts; do not invent labs; no identifiers.

### 4.2 Output record extensions

Each `adapted_notes.jsonl` row should include at minimum:

- `context_schema_version`
- `prior_context_fingerprint` (hash of canonical JSON) **or** embed compact `prior_context` snapshot
- `groq_model` (per row)

Downstream (`07`) should prefer **per-row** model metadata over ambient env when present.

### 4.3 Single pass per adapted prior

- **One** Groq completion per prior visit that has `best_note_text` (current behavior), **plus** showcase path unchanged.
- Context file is built **without** requiring prior adapted notes.

---

## 5. Storage paths (repo)

| File | Purpose |
|------|---------|
| `data/staging/match_results.jsonl` | Source encounters |
| `data/staging/selected_patients_golden.jsonl` | Curated **19** demo / arc patients (~269 encounters) |
| `data/staging/patient_longitudinal_context.jsonl` | **New**: one row per encounter in scope |
| `data/staging/adapted_notes.jsonl` | Adapted outputs + provenance |

---

## 6. Operations

- **Resume:** Regenerate context if `match_results` or schema version changes; adapted rows should record fingerprint to detect staleness.
- **Models:** One **primary** Groq model per frozen demo bundle; avoid silent mixing in one artifact.
- **Dental / demo hygiene (optional flag):** Exclude or mask dental-only prior rows from the K-window tail for narrative demos.

---

## 7. What makes a **good demo**

### 7.1 Hero artifact

Not a standalone summary. Show **evidence → output**:

1. **Timeline:** last **3 priors + today** (date, reason, top conditions/meds, 1–2 obs lines).
2. **Context used:** bullets from longitudinal context (and optional 2–4 sentence summary if enabled).
3. **Today’s reference template** (truncated): labeled as **structure/style source** (external corpus).
4. **Adapted note** for today.

Optional: 2–3 **highlight callouts** (CC aligns with today’s reason; chronic backbone; acute handled).

### 7.2 Cohort

- **`selected_patients_golden.jsonl`:** **19** patients, **~269** encounters; good for depth and arc variety (GM / Pediatrics / Neurology / Psychiatry mix).
- For a **live ~5-minute** narrative, pick **one** patient and walk **3–6 consecutive visits** (scroll timeline + show pre-frozen or live-generated outputs).

### 7.3 Frozen bundle (rehearsals)

Keep together: `selected_patients_golden.jsonl`, `patient_longitudinal_context.jsonl` (once built), `adapted_notes.jsonl`, pinned **`GROQ_MODEL`**, and `context_schema_version` / commit SHA.

---

## 8. Implementation checklist (next PR)

1. Add script: build `patient_longitudinal_context.jsonl` from `match_results` + `SCRIBE_SELECTED_PATIENTS_JSONL`.
2. Extend `06_adapt_notes.py`: load context by `(patient_id, encounter_id)`; extend prompt; extend output fields.
3. Update `07` provenance (`adapted_by` / metadata) to honor per-row `groq_model`.
4. (Optional) env `SCRIBE_PRIOR_VISITS`, `SCRIBE_CONTEXT_SUMMARY=0|1`.

---

## 9. Related paths in repo

- Adaptation: `data_prep/scripts/06_adapt_notes.py`
- Corpus: `data_prep/scripts/07_assemble_corpus.py`
- Demo cohort: `data/staging/selected_patients_golden.jsonl`
