"""
07_assemble_corpus.py — run from data_prep/
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import math


def _clean_json_str(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip().lower() in ("nan", "none", ""):
        return None
    return str(value)

from utils.io_utils import load_jsonl, write_jsonl
from utils.snomed_icd10_nlm import get_snomed_icd10_map, lookup_icd10_cm
from utils.synthea_demo_fields import encounter_demo_fields, patient_row_for_corpus
from utils.synthea_utils import load_synthea

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data/clinical_corpus_v2"


def _selected_patients_jsonl() -> Path:
    override = os.environ.get("SCRIBE_SELECTED_PATIENTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    golden = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
    if golden.is_file():
        return golden
    return REPO_ROOT / "data/staging/selected_patients.jsonl"

def _match_results_jsonl() -> Path:
    override = os.environ.get("SCRIBE_MATCH_RESULTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    golden = REPO_ROOT / "data/staging/match_results_golden.jsonl"
    if golden.is_file():
        return golden
    return REPO_ROOT / "data/staging/match_results.jsonl"

SELECTED_PATH = _selected_patients_jsonl()
NOTES_PATH = REPO_ROOT / "data/staging/adapted_notes.jsonl"
MATCHES_PATH = _match_results_jsonl()
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"


def _adapted_by(note: dict) -> str:
    if note.get("is_showcase") and note.get("reference_source") == "aci_bench":
        return "aci_bench_direct"
    return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def main() -> None:
    snomed_map = get_snomed_icd10_map(REPO_ROOT)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    for f in CORPUS_DIR.glob("*.jsonl"):
        f.unlink()

    synthea = load_synthea(SYNTHEA_DIR)
    selected = {p["patient_id"]: p for p in load_jsonl(SELECTED_PATH)}
    notes = {n["encounter_id"]: n for n in load_jsonl(NOTES_PATH)}
    matches_raw = list(load_jsonl(MATCHES_PATH))
    matches = {m["encounter_id"]: m for m in matches_raw if m["patient_id"] in selected}

    patients_df = synthea["patients"]
    encounters_df = synthea["encounters"]
    conditions_df = synthea["conditions"]
    meds_df = synthea["medications"]
    obs_df = synthea["observations"]

    counts = defaultdict(int)

    print("Writing patients.jsonl...")
    for pid, meta in selected.items():
        pt = patients_df[patients_df["Id"] == pid].iloc[0]
        write_jsonl(
            CORPUS_DIR / "patients.jsonl",
            patient_row_for_corpus(pid, pt, meta),
        )
        counts["patients"] += 1

    print("Writing encounters.jsonl...")
    for enc_id, match in matches.items():
        note = notes.get(enc_id, {})
        enc_rows = encounters_df[encounters_df["Id"] == enc_id]
        synthea_snap = (
            encounter_demo_fields(
                enc_rows.iloc[0],
                organizations=synthea.get("organizations"),
                providers=synthea.get("providers"),
                payers=synthea.get("payers"),
            )
            if not enc_rows.empty
            else None
        )

        encounter_record = {
            "encounter_id": enc_id,
            "patient_id": match["patient_id"],
            "encounter_date": match["encounter_date"],
            "specialty": match["specialty"],
            "reason": _clean_json_str(match.get("encounter_reason")),
            "match_score": match["match_score"],
            "is_showcase": note.get("is_showcase", False),
            "has_dialogue": note.get("has_dialogue", False),
        }
        if synthea_snap:
            encounter_record["synthea_encounter"] = synthea_snap

        write_jsonl(CORPUS_DIR / "encounters.jsonl", encounter_record)
        counts["encounters"] += 1

    print("Writing notes.jsonl...")
    for enc_id, note in notes.items():
        if note.get("patient_id") not in selected:
            continue
        write_jsonl(
            CORPUS_DIR / "notes.jsonl",
            {
                "note_id": note["adapted_note_id"],
                "encounter_id": enc_id,
                "patient_id": note["patient_id"],
                "note_text": note["note_text"],
                "reference_source": note.get("reference_source", ""),
                "reference_note_id": note.get("reference_note_id", ""),
                "is_showcase": note.get("is_showcase", False),
                "coherence_issues": note.get("coherence_issues", []),
            },
        )
        counts["notes"] += 1

    print("Writing dialogues.jsonl...")
    dlg_idx = 0
    for enc_id, note in notes.items():
        if not note.get("has_dialogue") or not note.get("dialogue"):
            continue
        if note.get("patient_id") not in selected:
            continue
        write_jsonl(
            CORPUS_DIR / "dialogues.jsonl",
            {
                "dialogue_id": f"dlg_{dlg_idx:06d}",
                "encounter_id": enc_id,
                "patient_id": note["patient_id"],
                "dialogue_text": note["dialogue"],
                "source": note.get("reference_source", ""),
                "is_showcase": note.get("is_showcase", False),
            },
        )
        dlg_idx += 1
        counts["dialogues"] += 1

    print("Writing conditions.jsonl...")
    cond_idx = 0
    for pid in selected:
        for _, cond in conditions_df[conditions_df["PATIENT"] == pid].iterrows():
            write_jsonl(
                CORPUS_DIR / "conditions.jsonl",
                {
                    "condition_id": f"cond_{cond_idx:06d}",
                    "patient_id": pid,
                    "snomed_code": str(cond["CODE"]),
                    "icd10_code": lookup_icd10_cm(snomed_map, cond["CODE"]),
                    "description": cond["DESCRIPTION"],
                    "onset_date": str(cond["START"])[:10],
                    "stop_date": str(cond["STOP"])[:10]
                    if pd.notna(cond["STOP"])
                    else None,
                    "is_active": pd.isna(cond["STOP"]),
                },
            )
            cond_idx += 1
            counts["conditions"] += 1

    print("Writing medications.jsonl...")
    med_idx = 0
    for pid in selected:
        for _, med in meds_df[meds_df["PATIENT"] == pid].iterrows():
            write_jsonl(
                CORPUS_DIR / "medications.jsonl",
                {
                    "medication_id": f"med_{med_idx:06d}",
                    "patient_id": pid,
                    "rxnorm_code": str(med.get("CODE", "")),
                    "description": med["DESCRIPTION"],
                    "start_date": str(med["START"])[:10],
                    "stop_date": str(med["STOP"])[:10]
                    if pd.notna(med.get("STOP"))
                    else None,
                    "is_active": pd.isna(med.get("STOP")),
                    "reason": med.get("REASONDESCRIPTION", ""),
                },
            )
            med_idx += 1
            counts["medications"] += 1

    print("Writing observations.jsonl...")
    obs_idx = 0
    for pid in selected:
        for _, ob in obs_df[obs_df["PATIENT"] == pid].iterrows():
            write_jsonl(
                CORPUS_DIR / "observations.jsonl",
                {
                    "observation_id": f"obs_{obs_idx:06d}",
                    "patient_id": pid,
                    "encounter_id": ob.get("ENCOUNTER", ""),
                    "loinc_code": str(ob.get("CODE", "")),
                    "description": ob["DESCRIPTION"],
                    "value": str(ob.get("VALUE", "")),
                    "units": ob.get("UNITS", ""),
                    "date": str(ob["DATE"])[:10],
                },
            )
            obs_idx += 1
            counts["observations"] += 1

    print("Writing source_provenance.jsonl...")
    for enc_id, match in matches.items():
        note = notes.get(enc_id, {})
        write_jsonl(
            CORPUS_DIR / "source_provenance.jsonl",
            {
                "encounter_id": enc_id,
                "patient_id": match["patient_id"],
                "note_source": note.get("reference_source", "none"),
                "reference_note_id": note.get("reference_note_id", ""),
                "match_score": match["match_score"],
                "adapted_by": _adapted_by(note),
                "is_showcase": note.get("is_showcase", False),
            },
        )

    manifest = {
        "corpus_name": "Scribe-IQ Clinical Corpus v2.0",
        "corpus_version": "2.0",
        "corpus_tag": "v2",
        "predecessor_snapshot": "data/clinical_corpus_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthea_seed": 42,
        "synthea_population": 1000,
        "selected_patients": counts["patients"],
        "record_counts": {
            "patients": counts["patients"],
            "encounters": counts["encounters"],
            "notes": counts["notes"],
            "dialogues": counts["dialogues"],
            "conditions": counts["conditions"],
            "medications": counts["medications"],
            "observations": counts["observations"],
        },
        "sources": {
            "patient_spine": "Synthea v3 (seed=42)",
            "note_pool": "MTSamples (CC0), MedSynth (HF), ACI-Bench (CC BY)",
            "note_adaptation": "Groq / " + os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        },
        "files": [str(f.name) for f in sorted(CORPUS_DIR.glob("*.jsonl"))],
    }
    (CORPUS_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"\n✓ Corpus assembled under {CORPUS_DIR}")
    for entity, count in counts.items():
        print(f"  {entity:<20} {count:>6}")


if __name__ == "__main__":
    main()
