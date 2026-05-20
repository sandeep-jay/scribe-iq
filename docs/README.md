# Documentation index

Canonical entry point for Scribe IQ documentation. Start with the **overview** section if this is your first visit. For a two-minute **what runs now** spine that points at the baseline, see [architecture/CURRENT.md](architecture/CURRENT.md).

---

## Overview (read first)

| Doc | What it is for |
|-----|----------------|
| [overview/PORTFOLIO_CASE_STUDY.md](overview/PORTFOLIO_CASE_STUDY.md) | Product case study: problem, workflows, architecture, governance boundaries, and production limits |
| [overview/RESUME_SNIPPETS.md](overview/RESUME_SNIPPETS.md) | Reusable resume/project descriptions |
| [overview/PRODUCT_CONTEXT.md](overview/PRODUCT_CONTEXT.md) | Problem framing, scope, what is deferred and why |
| [overview/SYSTEM_OVERVIEW.md](overview/SYSTEM_OVERVIEW.md) | Diagrams, capability flags, extension seams (rationale in DESIGN_NOTES) |
| [overview/DESIGN_NOTES.md](overview/DESIGN_NOTES.md) | Builder's perspective: alternatives considered, what was non-obvious, what would change for production |
| [overview/PRIVACY_AND_PROVIDER_BOUNDARIES.md](overview/PRIVACY_AND_PROVIDER_BOUNDARIES.md) | Synthetic data boundary, provider egress, audit redaction, and PHI caveats |

## Run and operate

| Doc | What it is for |
|-----|----------------|
| [guides/QUICKSTART.md](guides/QUICKSTART.md) | One supported path to a working local system |
| [guides/LLM_AND_EMBEDDING_PROVIDERS.md](guides/LLM_AND_EMBEDDING_PROVIDERS.md) | LLM and embedding provider setup (Groq, Azure OpenAI, Bedrock) |
| [guides/README.md](guides/README.md) | Contributor setup and conventions |

## As-built reference

| Doc | What it is for |
|-----|----------------|
| [architecture/IMPLEMENTED_BASELINE.md](architecture/IMPLEMENTED_BASELINE.md) | Authoritative inventory: routes, schema, env flags |
| [architecture/CURRENT.md](architecture/CURRENT.md) | Short narrative of what runs today |
| [architecture/README.md](architecture/README.md) | Architecture hub with pillar links |

## Per-pillar READMEs

| Pillar | Location |
|--------|----------|
| Backend (FastAPI) | [`backend/README.md`](../backend/README.md) |
| Frontend (Next.js) | [`frontend/README.md`](../frontend/README.md) |
| Offline corpus pipeline | [`data_prep/README.md`](../data_prep/README.md) |

## Corpus pipeline reference

- [reference/corpus_offline_pipeline_v2_brief.md](reference/corpus_offline_pipeline_v2_brief.md) — execution source of truth for scripts `01`–`09`
- [reference/data_prep_adapt_notes_longitudinal_design.md](reference/data_prep_adapt_notes_longitudinal_design.md) — adapt notes plus longitudinal context contract

## Roadmaps

| Doc | Scope |
|-----|-------|
| [roadmap/SCRIBE_IQ_UI_ROADMAP.md](roadmap/SCRIBE_IQ_UI_ROADMAP.md) | UI roadmap (forward-looking) |

When a roadmap disagrees with [`architecture/IMPLEMENTED_BASELINE.md`](architecture/IMPLEMENTED_BASELINE.md), trust the baseline until the roadmap is updated.

## Archived design lineage

| Doc | What it is for |
|-----|----------------|
| [archive/README.md](archive/README.md) | Superseded roadmaps, design drafts, and hygiene checklists with successor pointers |

## Visual assets

- README and social showcase images: [assets/showcase/readme/](assets/showcase/readme/) and [assets/showcase/social/og.png](assets/showcase/social/og.png)
- UI mockups and screenshots: [design/README.md](design/README.md)

## Lineage and history

- [history/EVOLUTION.md](history/EVOLUTION.md) — short timeline of how the layout and docs evolved
- [archive/README.md](archive/README.md) — superseded prompts and drafts kept for record
- Archived precursor scripts: [`corpus_pipelines/agbonnet_hf_clinical_notes/`](../corpus_pipelines/agbonnet_hf_clinical_notes/) — preserved for reference; do not extend

## Generated artifacts

Output of the corpus pipeline, not hand-maintained specs:

- `data/clinical_corpus_v2/dataset_card.md`
- `data/clinical_corpus_v2/audit_report.md`
