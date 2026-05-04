"""
02_build_note_pool.py — run from repo: python data_prep/scripts/02_build_note_pool.py
   (or cd data_prep && python scripts/02_build_note_pool.py)

ACI-Bench: expects a clone under data/raw/aci_bench with wyim/aci-bench style pairs:
  train.csv + train_metadata.csv (dialogue + note columns). Override dir with
  SCRIBE_ACI_BENCH_DIR. If no usable local CSVs, loads mkieffer/ACI-Bench from HuggingFace.
"""
from __future__ import annotations


import os
import re
import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


from pathlib import Path

import pandas as pd
from datasets import load_dataset
from tqdm import tqdm

from utils.io_utils import count_jsonl, load_jsonl, write_jsonl
from utils.mappings import ICD10_TO_SPECIALTY, MTSAMPLES_TO_STANDARD_SPECIALTY

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "data/staging/note_pool.jsonl"
ACI_DIR = REPO_ROOT / "data/raw/aci_bench"
ACI_HF_ID = "mkieffer/ACI-Bench"
ACI_HF_CONFIGS = ("aci", "virtassist", "virtscribe")
ACI_HF_SPLITS = ("train", "valid", "test1", "test2", "test3")
RAW_MEDSYNTH = REPO_ROOT / "data/raw/hf_medsynth/train.jsonl"
RAW_MTSAMPLES = REPO_ROOT / "data/raw/hf_mtsamples/train.jsonl"


def _aci_bench_dir() -> Path:
    override = os.environ.get("SCRIBE_ACI_BENCH_DIR", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    return ACI_DIR


def _chief_complaint_from_note(note_text: str) -> str:
    t = (note_text or "").strip()
    if not t:
        return ""
    m = re.search(r"(?is)CHIEF COMPLAINT\s*\n+\s*([^\n]+)", t)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?im)^CC:\s*(.+)$", t)
    if m:
        return m.group(1).strip()
    return ""


def _build_aci_note(
    encounter_id: str,
    note_text: str,
    dialogue: str,
    *,
    chief_complaint: str = "",
    gender: str = "",
    patient_firstname: str = "",
    patient_familyname: str = "",
    doctor_name: str = "",
) -> dict | None:
    note_text = str(note_text or "").strip()
    if len(note_text) < 50:
        return None
    dlg = str(dialogue or "").strip()
    cc = (chief_complaint or "").strip() or _chief_complaint_from_note(note_text)
    gender_s = str(gender or "").strip()
    eid = str(encounter_id).strip()
    if not eid:
        return None
    return {
        "note_id": f"aci_{eid}",
        "source": "aci_bench",
        "specialty": "General Medicine",
        "icd10_code": None,
        "icd10_desc": None,
        "note_type": "full_encounter",
        "note_text": note_text,
        "dialogue": dlg if len(dlg) > 20 else None,
        "chief_complaint": cc,
        "gender": gender_s,
        "patient_name": f"{patient_firstname or ''} {patient_familyname or ''}".strip(),
        "doctor_name": str(doctor_name or ""),
        "word_count": len(note_text.split()),
        "quality_tier": "primary",
    }


def _iter_aci_local(root: Path, seen: set[str]):
    for meta_file in sorted(root.rglob("*_metadata.csv")):
        stem = meta_file.name.removesuffix("_metadata.csv")
        data_csv = meta_file.parent / f"{stem}.csv"
        try:
            meta_df = pd.read_csv(meta_file)
        except Exception as e:
            print(f"  Could not read {meta_file}: {e}")
            continue

        if data_csv.exists():
            try:
                body_df = pd.read_csv(data_csv)
            except Exception as e:
                print(f"  Could not read {data_csv}: {e}")
                continue
            merge_key = "encounter_id" if "encounter_id" in body_df.columns else "id"
            if merge_key not in meta_df.columns or merge_key not in body_df.columns:
                continue
            merged = meta_df.merge(body_df, on=merge_key, how="inner")
            for _, row in merged.iterrows():
                eid = str(row[merge_key]).strip()
                if not eid or eid in seen:
                    continue
                note_text = str(row.get("note") or row.get("tgt") or "")
                dialogue = str(row.get("dialogue") or row.get("src") or "")
                rec = _build_aci_note(
                    eid,
                    note_text,
                    dialogue,
                    chief_complaint=str(row.get("cc") or ""),
                    gender=str(row.get("patient_gender") or row.get("gender") or ""),
                    patient_firstname=str(row.get("patient_firstname") or ""),
                    patient_familyname=str(row.get("patient_familyname") or ""),
                    doctor_name=str(row.get("doctor_name") or ""),
                )
                if rec:
                    seen.add(eid)
                    yield rec
            continue

        src_tgt_candidates = sorted(meta_file.parent.glob("*src-tgt*.csv"))
        if not src_tgt_candidates:
            continue
        try:
            src_tgt_df = pd.read_csv(src_tgt_candidates[0])
        except Exception as e:
            print(f"  Could not read src-tgt: {e}")
            continue
        merge_key = "encounter_id" if "encounter_id" in src_tgt_df.columns else "id"
        if merge_key not in meta_df.columns:
            continue
        merged = meta_df.merge(src_tgt_df, on=merge_key, how="inner")
        for _, row in merged.iterrows():
            eid = str(row[merge_key]).strip()
            if not eid or eid in seen:
                continue
            note_text = str(row.get("note") or row.get("tgt") or "")
            dialogue = str(row.get("src") or "")
            rec = _build_aci_note(
                eid,
                note_text,
                dialogue,
                chief_complaint=str(row.get("cc") or ""),
                gender=str(row.get("patient_gender") or row.get("gender") or ""),
                patient_firstname=str(row.get("patient_firstname") or ""),
                patient_familyname=str(row.get("patient_familyname") or ""),
                doctor_name=str(row.get("doctor_name") or ""),
            )
            if rec:
                seen.add(eid)
                yield rec


def _iter_aci_huggingface(seen: set[str]):
    for config in ACI_HF_CONFIGS:
        ds_all = load_dataset(ACI_HF_ID, name=config)
        for split in ACI_HF_SPLITS:
            if split not in ds_all:
                continue
            for row in ds_all[split]:
                eid = str(row["encounter_id"]).strip()
                if not eid or eid in seen:
                    continue
                rec = _build_aci_note(eid, row["note"], row["dialogue"])
                if rec:
                    seen.add(eid)
                    yield rec


def normalize_icd10(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    try:
        return str(value).strip()
    except Exception:
        return ""


OUTPATIENT_KEYWORDS = [
    "progress note", "office visit", "office note", "soap",
    "follow-up", "followup", "follow up", "clinic note",
    "consult", "history and physical", "h&p", "outpatient",
    "checkup", "check-up", "annual", "wellness", "recheck",
]

EXCLUDED_SPECIALTIES = {
    "Surgery", "Neurosurgery", "Radiology", "Lab Medicine - Pathology",
    "Letters", "Discharge Summary", "Emergency Room Reports",
    "Autopsy", "IME-QME-Work Comp etc.", "Cosmetic / Plastic Surgery",
}


def is_outpatient_note(row) -> bool:
    if row.get("medical_specialty", "") in EXCLUDED_SPECIALTIES:
        return False
    text = f"{row.get('sample_name','')} {row.get('description','')}".lower()
    return any(kw in text for kw in OUTPATIENT_KEYWORDS)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)
    print("\n[1/3] Loading MedSynth...")
    if RAW_MEDSYNTH.exists():
        print(f"  from raw snapshot {RAW_MEDSYNTH}")
        medsynth = load_jsonl(RAW_MEDSYNTH)
    else:
        print("  from HuggingFace (no raw snapshot)\n  Tip: python scripts/export_note_sources_to_raw.py")
        medsynth = load_dataset("Ahmad0067/MedSynth", split="train")
    for idx, row in enumerate(tqdm(medsynth, desc="MedSynth")):
        icd10 = normalize_icd10(row.get("ICD10"))
        specialty = ICD10_TO_SPECIALTY.get(
            icd10[0] if icd10 else "X", "General Medicine"
        )
        note_text = (row.get("note") or row.get(" Note") or "").strip()
        dialogue = (row.get("dialogue") or row.get("Dialogue") or "").strip()
        if len(note_text) < 50:
            continue
        write_jsonl(
            OUTPUT,
            {
                "note_id": f"ms_{idx:06d}",
                "source": "medsynth",
                "specialty": specialty,
                "icd10_code": icd10,
                "icd10_desc": str(row.get("ICD10_desc") or ""),
                "note_type": "soap",
                "note_text": note_text,
                "dialogue": dialogue if dialogue else None,
                "chief_complaint": None,
                "gender": None,
                "word_count": len(note_text.split()),
                "quality_tier": "primary",
            },
        )
    print(f"  MedSynth done: {count_jsonl(OUTPUT)} records")

    print("\n[2/3] Loading MTSamples...")
    if RAW_MTSAMPLES.exists():
        print(f"  from raw snapshot {RAW_MTSAMPLES}")
        mtsamples = load_jsonl(RAW_MTSAMPLES)
    else:
        print("  from HuggingFace (no raw snapshot)")
        mtsamples = load_dataset("harishnair04/mtsamples", split="train")
    mts_count = 0
    for idx, row in enumerate(tqdm(mtsamples, desc="MTSamples")):
        if not is_outpatient_note(row):
            continue
        transcription = row.get("transcription") or ""
        if len(transcription) < 100:
            continue
        raw_specialty = (row.get("medical_specialty") or "General Medicine").strip()
        specialty = MTSAMPLES_TO_STANDARD_SPECIALTY.get(raw_specialty, raw_specialty)
        write_jsonl(
            OUTPUT,
            {
                "note_id": f"mts_{idx:06d}",
                "source": "mtsamples",
                "specialty": specialty,
                "icd10_code": None,
                "icd10_desc": None,
                "note_type": "progress_note",
                "note_text": transcription,
                "dialogue": None,
                "chief_complaint": row.get("description") or "",
                "gender": None,
                "keywords": row.get("keywords") or "",
                "word_count": len(transcription.split()),
                "quality_tier": "primary",
            },
        )
        mts_count += 1
    print(f"  MTSamples done: {mts_count} outpatient notes added")

    print("\n[3/3] Loading ACI-Bench...")
    aci_root = _aci_bench_dir()
    seen_ids: set[str] = set()
    aci_count = 0
    if aci_root.exists():
        for rec in _iter_aci_local(aci_root, seen_ids):
            write_jsonl(OUTPUT, rec)
            aci_count += 1
        if aci_count:
            print(f"  from local CSVs under {aci_root}")
    if aci_count == 0:
        if aci_root.exists():
            print(f"  No usable ACI CSV pairs under {aci_root}; loading HuggingFace {ACI_HF_ID} …")
        else:
            print(f"  {aci_root} not found; loading HuggingFace {ACI_HF_ID} …")
        for rec in _iter_aci_huggingface(seen_ids):
            write_jsonl(OUTPUT, rec)
            aci_count += 1
    print(f"  ACI-Bench done: {aci_count} encounters added")

    total = count_jsonl(OUTPUT)
    print(f"\n✓ Note pool complete: {total} total notes → {OUTPUT}")


if __name__ == "__main__":
    main()
