# Repository evolution (concise)

This file summarizes **layout and documentation** evolution so newcomers are not misled by older filenames or historical proposals.

## Corpus and lakehouse lineage

1. **Early-phase lakehouse-oriented tooling** was proposed and documented in **`reference-docs/CLINICAL_LAKEHOUSE_PROPOSAL_V2.md`** and older **`roadmap/PHASE1_MASTER_PLAN.md`** sections that referenced a **`lakehouse/`** script tree.
2. **Current canonical offline builder** for the demo corpus is **`data_prep/`** (see root **`README.md`** and **`reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md`**). Scripts live under `data_prep/scripts/` with supporting README text.
3. **Optional local archive:** **`lakehouse-old/`** may exist on a developer machine (often gitignored). It is **not** the supported path for new work.

## Documentation hygiene (2026-05)

- Introduced **`docs/README.md`** as a single map.
- Moved superseded long prompts into **`docs/archive/`** with archive banners:
  - Former **`reference-docs/SCRIBE_IQ_DATA_PIPELINE_AGENT.md`** → **`docs/archive/SCRIBE_IQ_DATA_PIPELINE_AGENT.md`** (v1 prompt)
  - Former **`reference-docs/SCRIBE_IQ_SIMPLIFIED_IMPLEMENTATION_AGENT.md`** → **`docs/archive/SCRIBE_IQ_SIMPLIFIED_IMPLEMENTATION_AGENT.md`**
  - Former **`app docs/SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md`** → **`docs/archive/SCRIBE_IQ_APP_IMPLEMENTATION_GUIDE.md`** (duplicate narrative)
- **`docs/design/mockups/`** holds **HTML mockups**; **`docs/design/references/`** holds PNG screenshots (formerly **`ui-references/`**). Duplicate Markdown was removed in favor of **`reference-docs/`**.


- **Nested layout:** HTML mocks + screenshots now live under **`docs/design/`** (instead of top-level **`design/`**) so deployment/runtime dirs stay clearer at the repo root.

## Application capabilities

Authoritative **as-built** behavior, routes, flags, and schema notes live in **`reference-docs/SCRIBE_IQ_IMPLEMENTED_BASELINE.md`**. Roadmaps express intent and sequencing; when they disagree with the baseline, **trust the baseline** until the roadmap is updated.

## Git history

Fine-grained edits (file moves, checklist refreshes, banners) are recorded in git on branch **`docs/hygiene-pass`** and subsequent merges to **`main`**.
