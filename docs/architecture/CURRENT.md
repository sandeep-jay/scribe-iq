# Scribe IQ — current system (short take)

This file is a **compact narrative** of what Scribe IQ is today. Authoritative **as-built** detail — routes, env flags, schema rows, and file pointers — is **[IMPLEMENTED_BASELINE.md](./IMPLEMENTED_BASELINE.md)**.

For **problem framing, scope, and what is deferred**, see [../overview/PRODUCT_CONTEXT.md](../overview/PRODUCT_CONTEXT.md). For **diagrams and capability flags**, see [../overview/SYSTEM_OVERVIEW.md](../overview/SYSTEM_OVERVIEW.md).

## What it is

A **governed clinical documentation AI prototype**: an offline synthetic clinical corpus loaded into **Postgres + pgvector**, served by a FastAPI backend and Next.js frontend. Users browse synthetic patient charts and encounters, generate structured notes from transcripts when enabled, run grounded chat over embeddings, and — when flags allow — inspect **Responsible AI** audit surfaces.

## Where truth lives

| Concern | Doc |
|--------|-----|
| Implemented behavior (today) | [IMPLEMENTED_BASELINE.md](./IMPLEMENTED_BASELINE.md) |
| Documentation index | [../README.md](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md) |
| Architecture hub | [README.md](./README.md) |
| Product framing and deferred intent | [../overview/PRODUCT_CONTEXT.md](../overview/PRODUCT_CONTEXT.md) |
| Offline corpus build | `data_prep/` + [../reference/corpus_offline_pipeline_v2_brief.md](../reference/corpus_offline_pipeline_v2_brief.md) |
| Product / sequencing intent | [../roadmap/](../roadmap/) |

When a roadmap disagrees with the baseline, **trust the baseline** until the roadmap is updated.

## Repository anchors

- **Runtime:** `docker-compose.yml` (Postgres on host port **5433**), `backend/`, `frontend/`.
- **Data:** `data_prep/` builds the corpus the loader ingests; application reads via the backend loader paths documented in the baseline.

Last updated: **2026-05-20** (README positioning and corpus-artifact documentation pass).
