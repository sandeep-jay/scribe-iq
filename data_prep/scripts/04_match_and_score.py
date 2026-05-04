"""
04_match_and_score.py — run from data_prep/
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


import random
from collections import defaultdict
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from utils.io_utils import load_jsonl, write_jsonl
from utils.mappings import ICD10_TO_SPECIALTY, specialty_from_clinical_text
from utils.snomed_icd10_nlm import get_snomed_icd10_map
from utils.scoring import score_match
from utils.synthea_utils import get_active_conditions, get_active_medications, load_synthea

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
NOTE_POOL = REPO_ROOT / "data/staging/note_pool.jsonl"
ACI_RES = REPO_ROOT / "data/staging/aci_reservations.jsonl"
OUTPUT = REPO_ROOT / "data/staging/match_results.jsonl"

GM_SAMPLE_SIZE = 200


def _naive_ts(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.tzinfo is None:
        return ts
    return ts.tz_convert("UTC").tz_localize(None)



def _snomed_str(code) -> str | None:
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return None
    try:
        return str(int(float(code)))
    except (TypeError, ValueError):
        s = str(code).strip()
        if not s:
            return None
        return s.split(".")[0]


def _icd_from_conditions(active_conditions, snomed_map: dict) -> list:
    codes = [_snomed_str(c) for c in active_conditions["CODE"].tolist()]
    return list(filter(None, [snomed_map.get(c) for c in codes if c]))


def _condition_labels(active_conditions, enc) -> list:
    labels = active_conditions["DESCRIPTION"].tolist()
    labels = [x for x in labels if isinstance(x, str) and x.strip()]
    if labels:
        return labels
    ed = enc.get("DESCRIPTION")
    if ed is not None and not (isinstance(ed, float) and pd.isna(ed)):
        s = str(ed).strip()
        if s:
            return [s]
    return []




def _prioritize_icd10_codes(codes: list) -> list:
    """Put non-Z ICD-10-CM chapters first so specialty follows a clinical code when both exist."""
    if not codes:
        return codes

    def _key(c):
        s = str(c).strip().upper()
        return (s.startswith("Z"), s)

    return sorted(codes, key=_key)


def _resolve_specialty(
    icd10_codes: list,
    conditions_list: list,
    encounter_reason,
    encounter_description=None,
) -> str:
    """Prefer ICD chapter when specific; otherwise use free-text heuristics (no UMLS/SNOMED map)."""
    reason = encounter_reason if isinstance(encounter_reason, str) else ""
    if reason.strip().lower() in ("nan", "none", ""):
        reason = ""
    enc_desc = encounter_description if isinstance(encounter_description, str) else ""
    if enc_desc.strip().lower() in ("nan", "none", ""):
        enc_desc = ""
    letter = (icd10_codes[0][0] if icd10_codes else None)
    specialty = ICD10_TO_SPECIALTY.get(letter if letter else "X", "General Medicine")
    hint = specialty_from_clinical_text(*conditions_list, reason, enc_desc)
    if not icd10_codes:
        return hint or specialty
    if specialty == "General Medicine" and letter and str(letter).upper() in ("R", "Z"):
        return hint or specialty
    if letter and str(letter).upper() == "Z" and hint:
        return hint
    return specialty


def main() -> None:
    snomed_map = get_snomed_icd10_map(REPO_ROOT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)

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
    gm_fallback = gm_notes[:GM_SAMPLE_SIZE]

    print("\nNote pool by specialty:")
    for spec, notes in sorted(notes_by_specialty.items(), key=lambda x: -len(x[1])):
        print(f"  {spec:<30} {len(notes)}")
    print(f"  {'General Medicine fallback cap':<30} {GM_SAMPLE_SIZE}")

    print("\nLoading Synthea data...")
    synthea = load_synthea(SYNTHEA_DIR)
    patients_df = synthea["patients"]
    encounters_df = synthea["encounters"]
    conditions_df = synthea["conditions"]
    meds_df = synthea["medications"]
    obs_df = synthea["observations"]

    print(f"\nMatching {len(patients_df)} patients...")
    for patient_id in tqdm(patients_df["Id"].unique()):
        pt_row = patients_df[patients_df["Id"] == patient_id].iloc[0]
        birth_date = _naive_ts(pd.to_datetime(pt_row["BIRTHDATE"]))
        gender = pt_row["GENDER"]

        pt_encounters = encounters_df[encounters_df["PATIENT"] == patient_id].sort_values(
            "START"
        )
        if len(pt_encounters) < 3:
            continue

        for _, enc in pt_encounters.iterrows():
            enc_date = _naive_ts(pd.to_datetime(enc["START"], utc=True))
            age = int((enc_date - birth_date).days / 365.25)

            active_conditions = get_active_conditions(conditions_df, patient_id, enc_date)
            active_meds = get_active_medications(meds_df, patient_id, enc_date)
            recent_obs = obs_df[
                (obs_df["PATIENT"] == patient_id)
                & (pd.to_datetime(obs_df["DATE"]) <= enc_date)
            ].tail(10)

            icd10_codes = _icd_from_conditions(active_conditions, snomed_map)
            enc_snomed = _snomed_str(enc.get("CODE"))
            if not icd10_codes and enc_snomed:
                mapped = snomed_map.get(enc_snomed)
                if mapped:
                    icd10_codes = [mapped]

            icd10_codes = _prioritize_icd10_codes(icd10_codes)

            conditions_list = _condition_labels(active_conditions, enc)
            specialty = _resolve_specialty(
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

            write_jsonl(
                OUTPUT,
                {
                    **enc_record,
                    "best_note_id": best_note["note_id"] if best_note else None,
                    "best_note_source": best_note["source"] if best_note else None,
                    "best_note_text": best_note["note_text"] if best_note else None,
                    "best_note_dialogue": best_note.get("dialogue") if best_note else None,
                    "match_score": best_score,
                },
            )

    print(f"\n✓ Matching complete → {OUTPUT}")


if __name__ == "__main__":
    main()
