# Repository evolution (concise)

This file summarizes **layout and documentation** evolution so newcomers are not misled by older filenames or historical proposals.

**Where to start today:** repository root [`README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/README.md) (product entry + screenshots) and [`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md) (full map). Narrative layers: [`docs/overview/`](../overview/) (product framing, diagrams, design rationale).

## Corpus and lakehouse lineage

1. **Early-phase lakehouse-oriented tooling** was proposed and documented in **`docs/archive/agbonnet_lakehouse_precursor_proposal_v2.md`** (historical banner; not the runnable pipeline today) and older **`docs/archive/PHASE1_MASTER_PLAN.md`** sections that referenced a **`lakehouse/`** script tree.
2. **Current canonical offline builder** for the demo corpus is **`data_prep/`** (see root [`README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/README.md), [`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md), and [`docs/reference/corpus_offline_pipeline_v2_brief.md`](../reference/corpus_offline_pipeline_v2_brief.md)). Scripts live under `data_prep/scripts/` with supporting README text.
3. **Optional local archive:** **`corpus_pipelines/agbonnet_hf_clinical_notes/`** may exist on a developer machine (often gitignored). It is **not** the supported path for new work.

## Documentation hygiene (2026-05)

- Recorded the detailed checklist for the hygiene pass in **[`docs/archive/WORK_PLAN_DOC_HYGIENE.md`](../archive/WORK_PLAN_DOC_HYGIENE.md)** (now marked **completed**; use that file for step-level history, this file for the summary).
- Introduced **`docs/README.md`** as a single map.
- Moved superseded long prompts into **`docs/archive/`** with archive banners:
  - Former **`reference-docs/SCRIBE_IQ_DATA_PIPELINE_AGENT.md`** → **`docs/archive/SCRIBE_IQ_DATA_PIPELINE_AGENT.md`** (v1 prompt)
  - Former **`reference-docs/SCRIBE_IQ_SIMPLIFIED_IMPLEMENTATION_AGENT.md`** → **`docs/archive/SCRIBE_IQ_SIMPLIFIED_IMPLEMENTATION_AGENT.md`**
  - Former **`app docs/SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md`** → **`docs/archive/SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md`** (duplicate narrative)
- **`docs/design/mockups/`** holds **HTML mockups**; **`docs/design/references/`** holds PNG screenshots (formerly **`ui-references/`**). Duplicate Markdown was removed in favor of **`docs/reference/`**.


- **Nested layout:** HTML mocks + screenshots now live under **`docs/design/`** (instead of top-level **`design/`**) so deployment/runtime dirs stay clearer at the repo root.


## Documentation layout consolidation (2026-05)

- Former top-level **`reference-docs/`** tree → **`docs/reference/`** (long-form engineering references).
- Former top-level **`roadmap/`** tree → **`docs/roadmap/`** (plans and sequencing).
- **`SCRIBE_IQ_IMPLEMENTED_BASELINE.md`** → **`docs/architecture/IMPLEMENTED_BASELINE.md`**; added **`docs/architecture/CURRENT.md`** as a short "current system" companion that points at the baseline.
- Added **`docs/architecture/README.md`** as an architecture hub (baseline links plus README entrypoints for `backend/`, `frontend/`, `data_prep/`, and archived **`corpus_pipelines/agbonnet_hf_clinical_notes/`**).

## Overview layer and quickstart (2026-05)

- Added **`docs/overview/`**: [`PRODUCT_CONTEXT.md`](../overview/PRODUCT_CONTEXT.md) (problem, scope, deferred), [`SYSTEM_OVERVIEW.md`](../overview/SYSTEM_OVERVIEW.md) (Mermaid diagrams, capability flags, extension seams), [`DESIGN_NOTES.md`](../overview/DESIGN_NOTES.md) (alternatives considered and production deltas).
- Added **[`docs/guides/QUICKSTART.md`](../guides/QUICKSTART.md)** as the fastest supported path to a running UI.
- Refocused **root [`README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/README.md)** on the entry table, stack, keys, screenshots, and a short pointer to overview docs (deep rationale lives in **`DESIGN_NOTES`**; diagrams in **`SYSTEM_OVERVIEW`**).
- Refocused **[`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md)** so **`docs/overview/`** leads; lineage and reference sections remain below the fold.

## Portfolio documentation consolidation (2026-05)

- Established the overview layer as the **product narrative** entrypoint. Added [`docs/overview/PORTFOLIO_CASE_STUDY.md`](../overview/PORTFOLIO_CASE_STUDY.md) (product case study with higher-ed to healthcare bridge, intentionally-not-production list, and extension plan) and [`docs/overview/RESUME_SNIPPETS.md`](../overview/RESUME_SNIPPETS.md) (generic, healthcare-targeted, and LinkedIn-length descriptions).
- Added [`docs/guides/LLM_AND_EMBEDDING_PROVIDERS.md`](../guides/LLM_AND_EMBEDDING_PROVIDERS.md) as the canonical provider-configuration matrix (Groq demo defaults, Azure OpenAI with legacy `AZURE_OPENAI_DEPLOYMENT` / `AZURE_OPENAI_MINI_DEPLOYMENT` aliases, Bedrock with `BEDROCK_PROFILE_NAME` and JSON-mode note, embedding-rebuild workflow, troubleshooting table).
- Tightened [`docs/overview/SYSTEM_OVERVIEW.md`](../overview/SYSTEM_OVERVIEW.md) to lead with the configurable LLM/embedding posture (Groq / Azure OpenAI / Bedrock) and to call out the provider boundary as a distinct section; replaced the OpenAI-only corpus-lifecycle text with "configured embedding provider".
- Extended [`docs/overview/PRIVACY_AND_PROVIDER_BOUNDARIES.md`](../overview/PRIVACY_AND_PROVIDER_BOUNDARIES.md) with a provider-modes table (demo / Azure / AWS / mixed), an embedding-provider caveat, and a product-interpretation section.
- Updated [`docs/guides/QUICKSTART.md`](../guides/QUICKSTART.md) to note Groq/OpenAI as the simplest local defaults with a pointer to the new provider guide; rephrased the Chat 503 troubleshooting line to "configured embedding provider + `scribe-load-corpus --embed`".
- Added the new provider guide to the "Run each pillar" table in [`docs/guides/README.md`](../guides/README.md).
- Moved **9 superseded long-form plan and design files into [`docs/archive/`](../archive/)** with archive banners so the active `docs/` tree only contains living documents: `PHASE1_MASTER_PLAN.md`, `SCRIBE_IQ_V1_IMPLEMENTATION_PLAN.md`, `SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md`, `SCRIBE_IQ_DATA_PIPELINE_AGENT.md`, `SCRIBE_IQ_LLM_PROVIDER_LAYER.md`, `SCRIBE_IQ_RESPONSIBLE_AI_ROADMAP.md`, `SCRIBE_IQ_SIMPLIFIED_IMPLEMENTATION_AGENT.md`, `rag_app_phase1_mvp_design.md`, `rag_clinical_note_llm_design.md`, plus `agbonnet_lakehouse_precursor_proposal_v2.md` and `performance_improvement_plan_2026_05_06.md`. Inbound links from [`docs/design/README.md`](../design/README.md) and [`corpus_pipelines/agbonnet_hf_clinical_notes/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/corpus_pipelines/agbonnet_hf_clinical_notes/README.md) were updated to point at the new archive locations; [`docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md`](../roadmap/SCRIBE_IQ_UI_ROADMAP.md) gained a "Last reviewed" status header marking it as a forward-looking UI plan with as-built behavior recorded in [`IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md).

## Application capabilities

Authoritative **as-built** behavior, routes, flags, and schema notes live in **`docs/architecture/IMPLEMENTED_BASELINE.md`**. Roadmaps express intent and sequencing; when they disagree with the baseline, **trust the baseline** until the roadmap is updated.

## Git history

Fine-grained edits (file moves, checklist refreshes, banners) are recorded in git on branch **`docs/hygiene-pass`** and subsequent merges to **`main`**, and on follow-up documentation branches (for example `docs/project-documentation-overhaul`).
