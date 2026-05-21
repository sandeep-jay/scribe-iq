# Corpus artifacts

This guide explains what the generated Scribe IQ corpus contains, where the source material comes from, how the offline pipeline builds it, and what to do when `data/clinical_corpus_v2/` is missing.

Pipeline execution details live in [`data_prep/README.md`](../../data_prep/README.md). Script-by-script implementation detail lives in the [corpus pipeline reference](../reference/corpus_offline_pipeline_v2_brief.md). The generated artifact, when restored locally, also includes its own [`dataset_card.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data/clinical_corpus_v2/dataset_card.md), [`manifest.json`](https://github.com/sandeep-jay/scribe-iq/blob/main/data/clinical_corpus_v2/manifest.json), and [`audit_report.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data/clinical_corpus_v2/audit_report.md).

## Short version

Scribe IQ separates corpus construction from runtime serving. The application does not build patients, notes, longitudinal context, or embeddings on request. The offline `data_prep/` pipeline produces a validated generated artifact under `data/clinical_corpus_v2/`, and the backend loader imports that artifact into Postgres. Embeddings are generated later by `scribe-load-corpus --embed` using the configured embedding provider.

The current restored corpus artifact is a small synthetic demonstration cohort:

| Entity | Count |
|---|---:|
| Patients | 19 |
| Encounters | 269 |
| Notes | 269 |
| Dialogues | 19 |
| Conditions | 331 |
| Medications | 40 |
| Observations | 3,538 |

These counts are artifact-specific. Validate any restored artifact against `data/clinical_corpus_v2/manifest.json` rather than assuming the same numbers after a rerun.

## Source datasets

Scribe IQ uses synthetic and public source material only. No real patient data or PHI is used.

| Source | Role in the corpus | Notes / license posture |
|---|---|---|
| [Synthea](https://github.com/synthetichealth/synthea) | Synthetic patient spine: demographics, encounters, conditions, medications, observations, and longitudinal structure | Current artifact was generated from Synthea v3 with seed `42`; Synthea is Apache 2.0 licensed |
| [MTSamples](https://huggingface.co/datasets/harishnair04/mtsamples) | Public outpatient-style clinical note examples used as reference prose | CC0 dataset mirror used by the pipeline |
| [MedSynth](https://huggingface.co/datasets/Ahmad0067/MedSynth) | Synthetic SOAP-style notes and dialogue/note pairs used as note candidates | Hugging Face dataset terms apply |
| [ACI-Bench](https://huggingface.co/datasets/mkieffer/ACI-Bench) | Encounter dialogue examples reserved for showcase workflows | CC BY 4.0; current artifact includes 19 dialogues and 7 ACI-sourced notes |
| Groq / configured LLM provider | Note adaptation for patient-level consistency where the pipeline marks generated/adapted rows | Current artifact records Groq / `llama-3.3-70b-versatile` in `manifest.json` |

The important design point is that Synthea supplies the structured longitudinal patient record, while public note corpora supply realistic note shapes. The pipeline matches and adapts notes into the synthetic patient context instead of treating public note text as real patient history.

## What is in `data/clinical_corpus_v2/`

`data/clinical_corpus_v2/` is generated output. It may be restored locally for demos, but it is not treated as hand-authored application source.

| File | Purpose |
|---|---|
| `patients.jsonl` | Synthetic patient rows selected for the demo cohort |
| `encounters.jsonl` | Synthetic encounter timeline loaded into the application |
| `notes.jsonl` | Adapted clinical notes linked to encounters; loaded into Postgres and optionally embedded |
| `dialogues.jsonl` | Showcase encounter dialogues used by note-generation demos where available |
| `conditions.jsonl` | Synthea-derived condition history |
| `medications.jsonl` | Synthea-derived medication history |
| `observations.jsonl` | Synthea-derived observations |
| `source_provenance.jsonl` | Source and adaptation provenance for corpus rows |
| `manifest.json` | Machine-readable artifact metadata, counts, source summary, and file list |
| `dataset_card.md` | Human-readable dataset card with source datasets, counts, specialty mix, and reproduction summary |
| `audit_report.md` | Validation/audit summary from the corpus build |

The backend loader reads the JSONL artifact and upserts records into Postgres. Runtime API routes read from Postgres; they do not read directly from raw source snapshots or staging intermediates.

## Build approach

The corpus lifecycle is intentionally data-product style:

`raw sources` -> `staging intermediates` -> `curated corpus artifact` -> `Postgres loader` -> `runtime API/UI`

At a high level, the pipeline does this:

1. Generate a deterministic Synthea population and export structured clinical data.
2. Build a note pool from public note/dialogue datasets.
3. Reserve ACI-Bench encounters for showcase dialogue workflows.
4. Match candidate notes to synthetic encounters and score fit.
5. Select a small demo cohort with enough longitudinal depth and note quality.
6. Extract longitudinal context so adapted notes can reflect prior visits.
7. Adapt notes with the configured LLM provider while preserving structured patient constraints.
8. Assemble the curated JSONL artifact.
9. Generate the dataset card and validate the final corpus.

The application starts after step 9. Loading and embedding are operational steps performed by the backend tooling:

```bash
scribe-load-corpus
scribe-load-corpus --embed
```

## Validation and review signals

The artifact is meant to show data engineering discipline, not clinical realism at production scale. Reviewers should look for these signals:

- raw/staging/curated separation,
- reproducible pipeline steps,
- deterministic Synthea seed recorded in the manifest,
- explicit source provenance,
- dataset card and manifest generated with the artifact,
- validation/audit report,
- loader contract into serving storage,
- separation between note adaptation and runtime LLM workflows.

The current artifact's note source breakdown is 262 MedSynth-sourced notes and 7 ACI-Bench-sourced notes. The specialty distribution is 13 General Medicine, 3 Hematology, 1 Neurology, 1 Pediatrics, and 1 Pulmonology patients.

## Directory contract

| Path | Role | Committed? |
|---|---|---|
| `data/raw/` | Local source snapshots, downloads, Synthea export, optional ACI-Bench clone | No |
| `data/staging/` | Pipeline intermediates between scripts | No |
| `data/clinical_corpus_v2/` | Curated generated artifact loaded by `scribe-load-corpus` | Usually no |
| Postgres database | Runtime serving state, notes, embeddings, audit records | No |

## Limitations

- The corpus is synthetic and public-source adapted. It is not a clinical benchmark and must not be used for clinical decision-making.
- The cohort is intentionally small so reviewers can inspect the full shape of the system quickly.
- Notes are adapted for demo consistency, not validated clinical accuracy.
- Public-source note text and generated adaptation can carry artifacts from their source datasets and prompts.
- Restored artifact counts can differ from rerun counts if source snapshots, pipeline settings, or provider outputs change.

## Reviewer note

If `data/clinical_corpus_v2/` is absent after clone, that is expected unless a generated artifact has been restored. Rebuild or restore the generated artifact before running `scribe-load-corpus`.

For local run instructions, see [`QUICKSTART.md`](./QUICKSTART.md). For pipeline execution, see [`data_prep/README.md`](../../data_prep/README.md). For the long-form implementation brief, see the [corpus pipeline reference](../reference/corpus_offline_pipeline_v2_brief.md).
