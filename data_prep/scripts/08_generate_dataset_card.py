"""
08_generate_dataset_card.py — run from data_prep/
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from utils.io_utils import load_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data/clinical_corpus_v2"


def main() -> None:
    patients = list(load_jsonl(CORPUS_DIR / "patients.jsonl"))
    notes = list(load_jsonl(CORPUS_DIR / "notes.jsonl"))
    dialogues = list(load_jsonl(CORPUS_DIR / "dialogues.jsonl"))
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))

    specialty_dist = Counter(p["primary_specialty"] for p in patients)
    source_dist = Counter(n["reference_source"] for n in notes)

    card = f"""# Scribe-IQ Clinical Corpus

**Version:** 2.0  
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')} (UTC)  
**Pipeline:** `data_prep/`

---

## Summary

Synthetic clinical corpus of {len(patients)} patients for the Scribe-IQ demo.
Each patient has longitudinal encounters with notes and one showcase encounter
with dialogue where available.

Not for clinical use. Structured data: Synthea. Notes: MTSamples, MedSynth,
ACI-Bench, adapted via Groq where noted in `source_provenance.jsonl`.

---

## Source datasets

| Dataset | License | Role |
|---|---|---|
| Synthea v3 (seed=42) | Apache 2.0 | Patient spine |
| MTSamples | CC0 | Progress notes |
| MedSynth (Ahmad0067/MedSynth) | HuggingFace terms | SOAP-style notes |
| ACI-Bench | CC BY 4.0 | Encounter dialogues |

---

## Corpus statistics

| Entity | Count |
|---|---|
| Patients | {len(patients)} |
| Encounters | {manifest['record_counts'].get('encounters', 'N/A')} |
| Notes | {len(notes)} |
| Dialogues | {len(dialogues)} |
| Conditions | {manifest['record_counts'].get('conditions', 'N/A')} |
| Medications | {manifest['record_counts'].get('medications', 'N/A')} |

## Specialty distribution

| Specialty | Patients |
|---|---|
{chr(10).join(f'| {s} | {c} |' for s, c in sorted(specialty_dist.items()))}

## Note source breakdown

| Source | Notes |
|---|---|
{chr(10).join(f'| {s} | {c} |' for s, c in sorted(source_dist.items()))}

---

## Reproduction

```bash
cd data_prep
bash scripts/01_generate_patients.sh
python scripts/02_build_note_pool.py
python scripts/03_reserve_aci_encounters.py
python scripts/04_match_and_score.py
python scripts/05_select_patients.py
python scripts/06_adapt_notes.py
python scripts/07_assemble_corpus.py
python scripts/08_generate_dataset_card.py
python scripts/09_validate_corpus.py
```
"""

    (CORPUS_DIR / "dataset_card.md").write_text(card, encoding="utf-8")
    print(f"✓ dataset_card.md → {CORPUS_DIR}")


if __name__ == "__main__":
    main()
