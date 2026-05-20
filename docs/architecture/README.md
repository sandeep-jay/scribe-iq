# Architecture (current state)

Use this folder for **as-built** and **high-level current-system** documentation — not forward-looking roadmaps.

| Doc | Purpose |
|-----|---------|
| [CURRENT.md](CURRENT.md) | Short narrative of what runs today |
| [IMPLEMENTED_BASELINE.md](IMPLEMENTED_BASELINE.md) | Authoritative inventory: routes, env flags, schema, app surfaces |

**Product framing, diagrams, and design rationale:** [../overview/](../overview/) (`PRODUCT_CONTEXT`, `SYSTEM_OVERVIEW`, `DESIGN_NOTES`).

**Full documentation map:** [../README.md](../README.md).

## Implementation entrypoints (pillars)

How to run and extend each area; deep specs live under `docs/reference/` and per-folder READMEs.

| Area | Code | README |
|------|------|--------|
| Backend | `backend/` | [backend/README.md](../../backend/README.md) |
| Frontend | `frontend/` | [frontend/README.md](../../frontend/README.md) |
| Offline corpus (`data_prep/`) | `data_prep/` | [data_prep/README.md](../../data_prep/README.md) |

**Historical precursors (do not extend for new work):** [corpus_pipelines/agbonnet_hf_clinical_notes/](../../corpus_pipelines/agbonnet_hf_clinical_notes/) — see [corpus_pipelines/agbonnet_hf_clinical_notes/README.md](../../corpus_pipelines/agbonnet_hf_clinical_notes/README.md).

**Lineage:** [../history/EVOLUTION.md](../history/EVOLUTION.md). **Superseded drafts:** [../archive/](../archive/).
