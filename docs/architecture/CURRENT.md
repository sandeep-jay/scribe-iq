# Scribe IQ — current system (short take)

This file is a **compact narrative** of what Scribe IQ is today. Authoritative **as-built** detail—routes, env flags, schema rows, and file pointers—is **[IMPLEMENTED_BASELINE.md](./IMPLEMENTED_BASELINE.md)**.

## What it is

A **clinical documentation / RAG demo**: Next.js frontend + FastAPI backend over **Postgres + pgvector**. Users browse a synthetic patient corpus, open charts and encounters, generate structured notes from transcripts when enabled, run **chat over embeddings**, and—when flags allow—see **Responsible AI** audit surfaces.

## Where truth lives

| Concern | Doc |
|--------|-----|
| Implemented behavior (today) | [IMPLEMENTED_BASELINE.md](./IMPLEMENTED_BASELINE.md) |
| Documentation index | [../README.md](../README.md) |
| Offline corpus build | `data_prep/` + [../reference/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md](../reference/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md) |
| Product / sequencing intent | [../roadmap/](../roadmap/) |

When a roadmap disagrees with the baseline, **trust the baseline** until the roadmap is updated.

## Repository anchors

- **Runtime:** `docker-compose.yml` (Postgres on host port **5433**), `backend/`, `frontend/`.
- **Data:** `data_prep/` builds the corpus the loader ingests; application reads via the backend loader paths documented in the baseline.

Last updated: **2026-05-05** (documentation layout migration under `docs/`).
