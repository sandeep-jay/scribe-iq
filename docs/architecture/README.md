# Architecture (current state)

Use this folder for **as-built** and **high-level current-system** documentation — not forward-looking roadmaps.

| Doc | Purpose |
|-----|---------|
| [CURRENT.md](CURRENT.md) | Short narrative of what runs today |
| [IMPLEMENTED_BASELINE.md](IMPLEMENTED_BASELINE.md) | Authoritative inventory: routes, env flags, schema, app surfaces |

**Product framing, diagrams, and design rationale:** [../overview/](../overview/) (`PRODUCT_CONTEXT`, `SYSTEM_OVERVIEW`, `DESIGN_NOTES`).

**Full documentation map:** [../README.md](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md).

## Implementation entrypoints (pillars)

How to run and extend each area; deep specs live under `docs/reference/` and per-folder READMEs.

| Area | Code | README |
|------|------|--------|
| Backend | `backend/` | [backend/README.md](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/README.md) |
| Frontend | `frontend/` | [frontend/README.md](https://github.com/sandeep-jay/scribe-iq/blob/main/frontend/README.md) |
| Offline corpus (`data_prep/`) | `data_prep/` | [data_prep/README.md](https://github.com/sandeep-jay/scribe-iq/blob/main/data_prep/README.md) |

**Historical precursors (do not extend for new work):** [corpus_pipelines/agbonnet_hf_clinical_notes/](https://github.com/sandeep-jay/scribe-iq/tree/main/corpus_pipelines/agbonnet_hf_clinical_notes/) — see [corpus_pipelines/agbonnet_hf_clinical_notes/README.md](https://github.com/sandeep-jay/scribe-iq/blob/main/corpus_pipelines/agbonnet_hf_clinical_notes/README.md).

**Lineage:** [../history/EVOLUTION.md](../history/EVOLUTION.md). **Superseded drafts:** [../archive/](../archive/).
