# Documentation index

Start here for **human-maintained** specs, roadmaps, and archives. Generated corpus outputs may include Markdown under `data/` (see **Generated artifacts** below).

## Architecture (current state)

| Topic | Location |
|--------|-----------|
| **Architecture hub** (baseline + pillar links) | [architecture/README.md](architecture/README.md) |
| Current system (short narrative) | [architecture/CURRENT.md](architecture/CURRENT.md) |
| **As-built inventory** (API, schema, flags) | [architecture/IMPLEMENTED_BASELINE.md](architecture/IMPLEMENTED_BASELINE.md) |

## Four pillars — implementation / execution

| Pillar | README |
|--------|--------|
| Backend (FastAPI) | [backend/README.md](../backend/README.md) |
| Frontend (Next.js) | [frontend/README.md](../frontend/README.md) |
| Offline corpus builder (`data_prep/`) | [data_prep/README.md](../data_prep/README.md) |
| Archived AGBonnet / precursor (`lakehouse-old/`) | [lakehouse-old/README.md](../lakehouse-old/README.md) |

## Quick links

| Topic | Location |
|--------|-----------|
| Run / demo overview | [README.md](../README.md) |
| Design (mockups + screenshots) | [design/README.md](design/README.md) |

## Roadmaps (`docs/roadmap/`)

- [PHASE1_MASTER_PLAN.md](roadmap/PHASE1_MASTER_PLAN.md) — architecture / Phase 1 framing (historical `lakehouse/` paths → lineage; archived scripts: `lakehouse-old/`)
- [SCRIBE_IQ_UI_ROADMAP.md](roadmap/SCRIBE_IQ_UI_ROADMAP.md) — UI and related product surface
- [SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md](roadmap/SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md) — Responsible AI Control Center
- [SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md](roadmap/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md) — v1 checklist (status refreshed against baseline)

## Reference docs — corpus / `data_prep/` pipeline

**Execution source of truth for scripts `01`–`09`:** [reference/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md](reference/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md)

Supporting specs:

- [reference/ADAPT_NOTES_AND_LONGITUDINAL_CONTEXT.md](reference/ADAPT_NOTES_AND_LONGITUDINAL_CONTEXT.md) — adapt notes + longitudinal context (script `06` contract)
- [reference/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md](reference/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md) — **appendix** (implementation corrections narrative); canonical runner detail lives in the V2 brief above

## Reference docs — application design

- [reference/CLinical_Note_LLM.md](reference/CLinical_Note_LLM.md), [reference/SCRIBE_IQ_DESIGN_PHASE1.md](reference/SCRIBE_IQ_DESIGN_PHASE1.md)

## Historical precursor — AGBonnet / “lakehouse” lineage

- [reference/CLINICAL_LAKEHOUSE_PROPOSAL_V2.md](reference/CLINICAL_LAKEHOUSE_PROPOSAL_V2.md) — architectural proposal (historical; see banner). Archived runnable precursors: [lakehouse-old/README.md](../lakehouse-old/README.md)

## Process

- [reference/GIT_CHECKPOINTS.md](reference/GIT_CHECKPOINTS.md) — checkpoint branches before large UI/IA experiments

## Archive (`docs/archive/`)

Superseded prompts and drafts kept for history: [archive/README.md](archive/README.md).

## Evolution narrative

Short timeline of how layouts and docs evolved: [history/EVOLUTION.md](history/EVOLUTION.md).

## Hygiene work plan

Active checklist for this documentation pass: [WORK_PLAN_DOC_HYGIENE.md](WORK_PLAN_DOC_HYGIENE.md).

## Generated artifacts

These files are **outputs** of pipelines, not specs:

- `data/clinical_corpus_v2/audit_report.md`
- `data/clinical_corpus_v2/dataset_card.md`

Treat them as build metadata; link from here rather than duplicating them inside roadmaps.
