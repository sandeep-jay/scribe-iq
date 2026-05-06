# AGBonnet HF clinical notes pipeline (`corpus_pipelines/agbonnet_hf_clinical_notes/`)

This tree is the **Hugging Face augmented clinical notes** staging track (default dataset **`AGBonnet/augmented-clinical-notes`**): validate HF readiness, **stage** to local Parquet + `data/staging/manifest.json`, optional **medical-specialty classification**, export to JSONL, and an **interim seed-plan** helper. It is **not** the Synthea + scripts `01`–`09` flow under [`data_prep/`](../../data_prep/).

The **supported offline corpus builder** for the demo corpus in this repository remains **`data_prep/`** (see repository root [README.md](../../README.md) and [docs/reference/corpus_offline_pipeline_v2_brief.md](../../docs/reference/corpus_offline_pipeline_v2_brief.md)). Use this pipeline when you intentionally work the HF staging path or reproduce early Project L milestones.

---

## Why keep it

- **Working reference** for HF validate → stage → classify → export / interim seed planning.
- **Documentation lineage:** rationale and broader proposal narrative remain in [docs/reference/agbonnet_lakehouse_precursor_proposal_v2.md](../../docs/reference/agbonnet_lakehouse_precursor_proposal_v2.md).
- **Repository timeline:** [docs/history/EVOLUTION.md](../../docs/history/EVOLUTION.md).

For **architecture and current behavior** of the running app and loader, see [docs/architecture/README.md](../../docs/architecture/README.md).

---

## Layout on disk

| Path | Role |
|------|------|
| `corpus_pipelines/agbonnet_hf_clinical_notes/requirements.txt` | Python dependencies for these scripts only |
| `corpus_pipelines/agbonnet_hf_clinical_notes/scripts/` | Pipeline scripts (see table below) |
| Repo `data/staging/` | Typical outputs (`manifest.json`, Parquet, JSONL summaries) when these scripts are run |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate_dataset.py` | Probe HF dataset → readiness **VERDICT** |
| `scripts/stage_dataset.py` | Write Parquet + `data/staging/manifest.json` |
| `scripts/classify_specialties.py` | Local HF **`anaschahid/medical-specialty-classifier`** on staged rows → `specialty_predictions.jsonl` (specialty labels — **not** LDA topic modelling) |
| `scripts/export_staged_parquet_jsonl.py` | Export staged Parquet toward JSONL-style intermediates |
| `scripts/create_seed_plan.py` | **Interim** seed planning helper for early prototyping |
| `scripts/corpus_constants.py` | Shared dataset ids / column defaults |

---

## Setup (from repository root)

```bash
cd corpus_pipelines/agbonnet_hf_clinical_notes
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional HF cache (if `~/.cache/huggingface` is not writable):

```bash
export HF_HOME="$(pwd)/../../.hf_home"
mkdir -p "$HF_HOME"
```

---

## Run examples

With venv active and **`cwd` = `corpus_pipelines/agbonnet_hf_clinical_notes/`**:

```bash
python3 scripts/validate_dataset.py
python3 scripts/stage_dataset.py
python3 scripts/classify_specialties.py --batch-size 32 --device auto --repo-root ../..
python3 scripts/export_staged_parquet_jsonl.py --repo-root ../..
python3 scripts/create_seed_plan.py --repo-root ../..
```

From **repository root** (adjust if your venv lives under this directory’s `.venv`):

```bash
corpus_pipelines/agbonnet_hf_clinical_notes/.venv/bin/python corpus_pipelines/agbonnet_hf_clinical_notes/scripts/classify_specialties.py --device auto --repo-root .
```

---

## Relationship to the app and to `data_prep/`

Historical master-plan prose may refer to a generic **`lakehouse/`** tree; **this repository’s HF staging scripts live under `corpus_pipelines/agbonnet_hf_clinical_notes/`** (formerly `lakehouse-old/`). Product sequencing and application MVP details live in [docs/roadmap/PHASE1_MASTER_PLAN.md](../../docs/roadmap/PHASE1_MASTER_PLAN.md) — treat early **`lakehouse/`** path mentions there as **design lineage**, not mandatory paths today.

**For new demo corpus work** prefer **`data_prep/`** and the corpus brief; extend this tree only when you are changing the HF staging / classifier / seed-plan behavior itself.
