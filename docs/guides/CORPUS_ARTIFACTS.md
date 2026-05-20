# Corpus Artifacts

This guide explains the corpus artifact lifecycle and what to do when `data/clinical_corpus_v2/` is missing. Pipeline execution details live in [`data_prep/README.md`](../../data_prep/README.md) and the [corpus pipeline reference](../reference/corpus_offline_pipeline_v2_brief.md).

## Short version

Scribe IQ separates data construction from runtime serving. The app does not build patients, notes, or longitudinal context on request. The offline corpus pipeline produces a validated generated artifact, and the backend loader imports that artifact into Postgres.

## Lifecycle

`raw sources` -> `staging intermediates` -> `curated corpus artifact` -> `Postgres loader` -> `runtime API/UI`

## Directory contract

| Path | Role | Committed? |
|---|---|---|
| `data/raw/` | Local source snapshots | No |
| `data/staging/` | Pipeline intermediates | No |
| `data/clinical_corpus_v2/` | Curated generated artifact loaded by `scribe-load-corpus` | Usually no |
| Postgres database | Runtime serving state | No |

## Why this is data-product style

This is not a full enterprise data platform. It borrows the useful data-platform patterns:

- raw/staging/curated separation,
- reproducible pipeline steps,
- validation gates,
- dataset card,
- audit report,
- loader contract into serving storage.

## Reviewer note

If `data/clinical_corpus_v2/` is absent after clone, that is expected unless a generated artifact has been restored. The repository documents corpus construction and runtime serving separately.

For execution details, see [`data_prep/README.md`](../../data_prep/README.md) and the [corpus pipeline reference](../reference/corpus_offline_pipeline_v2_brief.md).
