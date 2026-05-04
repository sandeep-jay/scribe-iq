# Scribe-IQ `data_prep/` pipeline

Generates the **50-patient** demo corpus under `data/clinical_corpus_v2/`. Spec:
`../reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_CURSOR.md`.

Archived exploratory scripts live in **`../lakehouse-old/`**.

## Prerequisites

- Python 3.11+
- Java 11+ and `synthea-with-dependencies.jar` at **repo root** (for script 01)
- Optional: `GROQ_API_KEY` for script 06
- Optional: ACI-Bench clone at `data/raw/aci_bench`

## Setup

```bash
cd /path/to/scribe-iq
python3 -m venv data_prep/.venv
source data_prep/.venv/bin/activate
pip install -r data_prep/requirements.txt
```

## Repo layout (data)

| Path | Role |
|------|------|
| `data/raw/synthea/csv/` | Synthea CSV export (from `01`) |
| `data/raw/*` | Other raw sources (HF exports, ACI-Bench, …) |
| `data/staging/` | JSONL intermediates between steps |
| `data/clinical_corpus_v2/` | Final assembled corpus (`07`–`09`) |
| `data/snomed_icd10/vocabulary/` | Local OHDSI Athena CSVs (not committed) |

Use **`scripts/00_reset_pipeline_outputs.sh`** before a full rerun after regenerating Synthea or changing mapping logic. Add **`--corpus`** to also delete prior `clinical_corpus_v1` / `clinical_corpus_v2` outputs.

## Run (from `data_prep/`)

```bash
cd data_prep
bash scripts/00_reset_pipeline_outputs.sh --corpus   # optional clean slate
bash scripts/01_generate_patients.sh
python3 scripts/02_build_note_pool.py
python3 scripts/03_reserve_aci_encounters.py
python3 scripts/04_match_and_score.py
python3 scripts/05_select_patients.py
# Optional stratified demo cohort (20 patients, encounter band + quality ≥ 0.80):
# python3 scripts/05b_select_demo_patients.py
# export SCRIBE_SELECTED_PATIENTS_JSONL=data/staging/selected_patients_demo.jsonl
export GROQ_API_KEY=...
python3 scripts/06_adapt_notes.py
python3 scripts/07_assemble_corpus.py
python3 scripts/08_generate_dataset_card.py
python3 scripts/09_validate_corpus.py
```

Scripts append `data_prep` to `sys.path`, so you may also run
`python3 data_prep/scripts/02_....py` from the repo root.

## Outputs

- `data/staging/*.jsonl` — intermediate artifacts
- `data/clinical_corpus_v2/` — final JSONL + `manifest.json`, `audit_report.md`, `dataset_card.md` (older runs may still have `clinical_corpus_v1/`)
