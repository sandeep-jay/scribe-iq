# Documentation index

Start here for **human-maintained** specs, roadmaps, and archives. Generated corpus outputs may include Markdown under `data/` (see **Generated artifacts** below).

## Reading order (new contributors)

1. [architecture/CURRENT.md](architecture/CURRENT.md) — short “what runs now” spine  
2. [reference/corpus_offline_pipeline_v2_brief.md](reference/corpus_offline_pipeline_v2_brief.md) — offline corpus / `data_prep/` pipeline source of truth  
3. [architecture/README.md](architecture/README.md) — architecture hub (baseline + pillar README links)

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
| AGBonnet HF clinical notes (`corpus_pipelines/agbonnet_hf_clinical_notes/`) | [corpus_pipelines/agbonnet_hf_clinical_notes/README.md](../corpus_pipelines/agbonnet_hf_clinical_notes/README.md) |

## Quick links

| Topic | Location |
|--------|-----------|
| Run / demo overview | [README.md](../README.md) |
| Contributor guides (setup + when to update docs) | [guides/README.md](guides/README.md) |
| Design (mockups + screenshots) | [design/README.md](design/README.md) |

## Roadmaps (`docs/roadmap/`)

- [PHASE1_MASTER_PLAN.md](roadmap/PHASE1_MASTER_PLAN.md) — architecture / Phase 1 framing (historical `lakehouse/` paths → lineage; archived scripts: `corpus_pipelines/agbonnet_hf_clinical_notes/`)
- [SCRIBE_IQ_UI_ROADMAP.md](roadmap/SCRIBE_IQ_UI_ROADMAP.md) — UI and related product surface
- [SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md](roadmap/SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md) — Responsible AI Control Center
- [SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md](roadmap/SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md) — v1 checklist (status refreshed against baseline)

## Reference docs — corpus / `data_prep/` pipeline

**Execution source of truth for scripts `01`–`09`:** [reference/corpus_offline_pipeline_v2_brief.md](reference/corpus_offline_pipeline_v2_brief.md)

Supporting specs:

- [reference/data_prep_adapt_notes_longitudinal_design.md](reference/data_prep_adapt_notes_longitudinal_design.md) — adapt notes + longitudinal context (script `06` contract)
- [archive/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md](archive/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md) — **supersession stub**; merged implementation corrections live in the corpus brief **Appendix** above

## Reference docs — application design

- [reference/rag_clinical_note_llm_design.md](reference/rag_clinical_note_llm_design.md), [reference/rag_app_phase1_mvp_design.md](reference/rag_app_phase1_mvp_design.md)

## Historical precursor — AGBonnet / “lakehouse” lineage

- [reference/agbonnet_lakehouse_precursor_proposal_v2.md](reference/agbonnet_lakehouse_precursor_proposal_v2.md) — architectural proposal (historical; see banner). Archived runnable precursors: [corpus_pipelines/agbonnet_hf_clinical_notes/README.md](../corpus_pipelines/agbonnet_hf_clinical_notes/README.md)

## Archive (`docs/archive/`)

Superseded prompts and drafts kept for history: [archive/README.md](archive/README.md).

## Evolution narrative

Short timeline of how layouts and docs evolved: [history/EVOLUTION.md](history/EVOLUTION.md).

## Hygiene work plan (completed)

Historical checklist for the 2026-05 documentation pass: [WORK_PLAN_DOC_HYGIENE.md](WORK_PLAN_DOC_HYGIENE.md) (see banner at top of that file). Summary: [history/EVOLUTION.md](history/EVOLUTION.md).

## Generated artifacts

These files are **outputs** of pipelines, not specs:

- `data/clinical_corpus_v2/audit_report.md`
- `data/clinical_corpus_v2/dataset_card.md`

Treat them as build metadata; link from here rather than duplicating them inside roadmaps.


## Reference

- [reference/performance_improvement_plan_2026_05_06.md](reference/performance_improvement_plan_2026_05_06.md) — backend meeting-prep latency review, fixes, and benchmark notes
