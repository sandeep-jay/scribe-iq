"""
04b_match_and_score_golden.py — run from data_prep/

Re-runs the same scoring/matching logic as 04_match_and_score.py, but only for
patients listed in selected_patients_golden.jsonl (or SCRIBE_SELECTED_PATIENTS_JSONL).

Writes golden-only results to data/staging/match_results_golden.jsonl (does not
modify match_results.jsonl from 04). Override with SCRIBE_MATCH_RESULTS_GOLDEN_JSONL.

Use after refreshing note_pool (e.g. new ACI rows) without rematching the full Synthea cohort.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

_DP_ROOT = Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))

import pandas as pd
from tqdm import tqdm

from utils.io_utils import load_jsonl
from utils.scoring import score_match
from utils.synthea_utils import get_active_conditions, get_active_medications, load_synthea

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
NOTE_POOL = REPO_ROOT / "data/staging/note_pool.jsonl"
ACI_RES = REPO_ROOT / "data/staging/aci_reservations.jsonl"
OUTPUT_GOLDEN_DEFAULT = REPO_ROOT / "data/staging/match_results_golden.jsonl"
GOLDEN_DEFAULT = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"


def _load_04_module():
    path = Path(__file__).resolve().parent / "04_match_and_score.py"
    spec = importlib.util.spec_from_file_location("scribe_match_04", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _golden_jsonl_path() -> Path:
    override = os.environ.get("SCRIBE_SELECTED_PATIENTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    return GOLDEN_DEFAULT


def _golden_output_path() -> Path:
    override = os.environ.get("SCRIBE_MATCH_RESULTS_GOLDEN_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    return OUTPUT_GOLDEN_DEFAULT


def main() -> None:
    m = _load_04_module()
    output_path = _golden_output_path()
    golden_path = _golden_jsonl_path()
    if not golden_path.exists():
        raise SystemExit(f"Golden cohort not found: {golden_path}")

    golden_patients = [
        json.loads(line)
        for line in golden_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    golden_ids = [p["patient_id"] for p in golden_patients]
    print(f"Golden cohort: {len(golden_ids)} patients from {golden_path.name}")

    snomed_map = m.get_snomed_icd10_map(REPO_ROOT)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reserved_aci_ids: set[str] = set()
    if ACI_RES.exists():
        reserved_aci_ids = {r["note_id"] for r in load_jsonl(ACI_RES)}
    print(f"Reserved ACI encounters excluded from pool: {len(reserved_aci_ids)}")

    all_notes = [n for n in load_jsonl(NOTE_POOL) if n["note_id"] not in reserved_aci_ids]
    print(f"Notes available for matching: {len(all_notes)}")

    notes_by_specialty: dict[str, list] = defaultdict(list)
    gm_notes: list = []
    for note in all_notes:
        spec = note["specialty"]
        notes_by_specialty[spec].append(note)
        if spec == "General Medicine":
            gm_notes.append(note)

    random.seed(42)
    random.shuffle(gm_notes)
    gm_fallback = gm_notes[: m.GM_SAMPLE_SIZE]

    print("\nNote pool by specialty:")
    for spec, notes in sorted(notes_by_specialty.items(), key=lambda x: -len(x[1])):
        print(f"  {spec:<30} {len(notes)}")
    print(f"  {'General Medicine fallback cap':<30} {m.GM_SAMPLE_SIZE}")

    print("\nLoading Synthea data...")
    synthea = load_synthea(SYNTHEA_DIR)
    patients_df = synthea["patients"]
    encounters_df = synthea["encounters"]
    conditions_df = synthea["conditions"]
    meds_df = synthea["medications"]
    obs_df = synthea["observations"]

    new_rows: list[dict] = []

    print(f"\nMatching {len(golden_ids)} golden patients...")
    for patient_id in tqdm(golden_ids):
        pt_rows = patients_df[patients_df["Id"] == patient_id]
        if pt_rows.empty:
            print(f"  WARNING: patient {patient_id} not in Synthea patients.csv — skipping")
            continue
        pt_row = pt_rows.iloc[0]
        birth_date = m._naive_ts(pd.to_datetime(pt_row["BIRTHDATE"]))
        gender = pt_row["GENDER"]

        pt_encounters = encounters_df[encounters_df["PATIENT"] == patient_id].sort_values(
            "START"
        )
        if len(pt_encounters) < 3:
            print(f"  WARNING: patient {patient_id} has <3 encounters — skipping")
            continue

        for _, enc in pt_encounters.iterrows():
            enc_date = m._naive_ts(pd.to_datetime(enc["START"], utc=True))
            age = int((enc_date - birth_date).days / 365.25)

            active_conditions = get_active_conditions(conditions_df, patient_id, enc_date)
            active_meds = get_active_medications(meds_df, patient_id, enc_date)
            recent_obs = obs_df[
                (obs_df["PATIENT"] == patient_id)
                & (pd.to_datetime(obs_df["DATE"]) <= enc_date)
            ].tail(10)

            icd10_codes = m._icd_from_conditions(active_conditions, snomed_map)
            enc_snomed = m._snomed_str(enc.get("CODE"))
            if not icd10_codes and enc_snomed:
                mapped = snomed_map.get(enc_snomed)
                if mapped:
                    icd10_codes = [mapped]

            icd10_codes = m._prioritize_icd10_codes(icd10_codes)

            conditions_list = m._condition_labels(active_conditions, enc)
            specialty = m._resolve_specialty(
                icd10_codes,
                conditions_list,
                enc.get("REASONDESCRIPTION", ""),
                enc.get("DESCRIPTION"),
            )
            med_labels = active_meds["DESCRIPTION"].tolist()
            med_labels = [x for x in med_labels if isinstance(x, str) and x.strip()]

            enc_record = {
                "patient_id": patient_id,
                "encounter_id": enc["Id"],
                "encounter_date": enc_date.isoformat(),
                "encounter_reason": enc.get("REASONDESCRIPTION", ""),
                "specialty": specialty,
                "age": age,
                "gender": gender,
                "icd10_codes": icd10_codes,
                "conditions": conditions_list,
                "medications": med_labels,
                "recent_obs": recent_obs[["DESCRIPTION", "VALUE", "UNITS"]].to_dict(
                    "records"
                ),
            }

            if specialty == "General Medicine":
                candidates = list(gm_fallback)
            else:
                candidates = notes_by_specialty.get(specialty, []) + gm_fallback

            best_note = None
            best_score = 0.0
            for note in candidates:
                s = score_match(enc_record, note)
                if s > best_score:
                    best_score = s
                    best_note = note

            new_rows.append(
                {
                    **enc_record,
                    "best_note_id": best_note["note_id"] if best_note else None,
                    "best_note_source": best_note["source"] if best_note else None,
                    "best_note_text": best_note["note_text"] if best_note else None,
                    "best_note_dialogue": best_note.get("dialogue") if best_note else None,
                    "match_score": best_score,
                }
            )

    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as out:
        for r in new_rows:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    tmp.replace(output_path)
    print(f"\n✓ Golden rematch complete → {output_path}")
    print(f"  Wrote rows (golden encounters only): {len(new_rows)}")


if __name__ == "__main__":
    main()
