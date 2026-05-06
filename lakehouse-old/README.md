# Archived precursor tooling (`lakehouse-old/`)

This directory is **not supported for new corpus work**. The canonical offline corpus pipeline for this repository is **`data_prep/`** (see repository root [README.md](../README.md) and [docs/reference/corpus_offline_pipeline_v2_brief.md](../docs/reference/corpus_offline_pipeline_v2_brief.md)).

What lives here is **historical Project L–style tooling** focused on **HF-hosted augmented-clinical-notes (AGBonnet-style) staging**, local Parquet materialization, and **optional downstream labeling with a Hugging Face medical-specialty classifier** — **not** the Synthea + scripts `01`–`09` flow under `data_prep/`.

---

## Why keep it

- **Reference implementation** for early corpus staging (`validate` → `stage` → classify → export / interim seed planning).
- **Documentation lineage:** rationale and broader proposal narrative remain in [docs/archive/agbonnet_lakehouse_precursor_proposal_v2.md](../docs/archive/agbonnet_lakehouse_precursor_proposal_v2.md).
- **Repository timeline:** [docs/history/EVOLUTION.md](../docs/history/EVOLUTION.md).

For **architecture and current behavior** of the running app and loader, see [docs/architecture/README.md](../docs/architecture/README.md).

---

## Layout on disk

| Path | Role |
|------|------|
| `lakehouse-old/requirements.txt` | Python dependencies for these scripts only |
| `lakehouse-old/scripts/` | Precursor scripts (see table below) |
| Repo `data/staging/` | Typical outputs (`manifest.json`, Parquet, JSONL summaries) when these scripts were run historically |

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
cd lakehouse-old
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional HF cache (if `~/.cache/huggingface` is not writable):

```bash
export HF_HOME="$(pwd)/../.hf_home"
mkdir -p "$HF_HOME"
```

---

## Run examples

With venv active and **`cwd` = `lakehouse-old/`**:

```bash
python3 scripts/validate_dataset.py
python3 scripts/stage_dataset.py
python3 scripts/classify_specialties.py --batch-size 32 --device auto --repo-root ..
python3 scripts/export_staged_parquet_jsonl.py --repo-root ..
python3 scripts/create_seed_plan.py --repo-root ..
```

From **repository root** (adjust path if your venv lives under `lakehouse-old/.venv`):

```bash
lakehouse-old/.venv/bin/python lakehouse-old/scripts/classify_specialties.py --device auto --repo-root .
```

---

## Relationship to the app and to `data_prep/`

Historical master-plan prose may refer to a generic **`lakehouse/`** tree; **this repository’s archived copy is `lakehouse-old/`**. Product sequencing and application MVP details live in [docs/roadmap/PHASE1_MASTER_PLAN.md](../docs/roadmap/PHASE1_MASTER_PLAN.md) — treat early **`lakehouse/`** path mentions there as **design lineage**, not mandatory paths today.

**Do not extend these scripts for new demo corpus work** — implement changes under **`data_prep/`** and update the V2 pipeline brief instead.
