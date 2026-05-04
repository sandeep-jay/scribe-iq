"""
09_validate_corpus.py — run from data_prep/
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


from collections import Counter
from pathlib import Path

from utils.io_utils import load_jsonl

def _load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return list(load_jsonl(path))


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "data/clinical_corpus_v2"


def main() -> None:
    patients = list(load_jsonl(CORPUS / "patients.jsonl"))
    encounters = list(load_jsonl(CORPUS / "encounters.jsonl"))
    notes = list(load_jsonl(CORPUS / "notes.jsonl"))
    dialogues = list(load_jsonl(CORPUS / "dialogues.jsonl"))
    conditions = _load_jsonl(CORPUS / "conditions.jsonl")
    medications = _load_jsonl(CORPUS / "medications.jsonl")

    patient_ids = {p["patient_id"] for p in patients}
    encounter_ids = {e["encounter_id"] for e in encounters}
    issues: list[str] = []
    warnings: list[str] = []

    for e in encounters:
        if e["patient_id"] not in patient_ids:
            issues.append(f"Encounter {e['encounter_id']} orphaned patient_id")
    for n in notes:
        if n["encounter_id"] not in encounter_ids:
            issues.append(f"Note {n['note_id']} orphaned encounter_id")
        if not n.get("note_text") or len(n["note_text"].split()) < 30:
            issues.append(f"Note {n['note_id']} empty or too short")
    for d in dialogues:
        if d["encounter_id"] not in encounter_ids:
            issues.append(f"Dialogue {d['dialogue_id']} orphaned encounter_id")

    showcase_enc_ids = {e["encounter_id"] for e in encounters if e.get("is_showcase")}
    dialogue_enc_ids = {d["encounter_id"] for d in dialogues}
    aci_dialogue_ids = {d["encounter_id"] for d in dialogues if "aci" in str(d.get("source", "")).lower()}
    showcase_with_dlg = showcase_enc_ids & dialogue_enc_ids
    showcase_aci_dlg = showcase_enc_ids & aci_dialogue_ids
    showcase_no_dlg = showcase_enc_ids - dialogue_enc_ids

    for enc_id in showcase_no_dlg:
        warnings.append(f"Showcase encounter {enc_id} has no dialogue")

    specialty_dist = Counter(p["primary_specialty"] for p in patients)
    source_dist = Counter(n["reference_source"] for n in notes)
    score_vals = [e["match_score"] for e in encounters]
    avg_score = sum(score_vals) / len(score_vals) if score_vals else 0.0

    print("=" * 55)
    print("CORPUS AUDIT")
    print("=" * 55)
    print("\nSCALE")
    print(f"  Patients:      {len(patients)}")
    print(f"  Encounters:    {len(encounters)}")
    print(f"  Notes:         {len(notes)}")
    print(f"  Dialogues:     {len(dialogues)}")
    print(f"  Conditions:    {len(conditions)}")
    print(f"  Medications:   {len(medications)}")
    print("\nSHOWCASE")
    print(f"  Total showcase:             {len(showcase_enc_ids)}")
    print(f"  Showcase with any dialogue: {len(showcase_with_dlg)}")
    print(f"  Showcase with ACI dialogue: {len(showcase_aci_dlg)}")
    print(f"  Showcase with no dialogue:  {len(showcase_no_dlg)}")
    print("\nSPECIALTY DISTRIBUTION")
    for spec, count in sorted(specialty_dist.items(), key=lambda x: -x[1]):
        print(f"  {spec:<30} {count}")
    print("\nNOTE SOURCES")
    for src, count in sorted(source_dist.items(), key=lambda x: -x[1]):
        print(f"  {src:<20} {count}")
    print("\nMATCH QUALITY")
    if score_vals:
        print(
            f"  Average: {avg_score:.3f}  Min: {min(score_vals):.3f}  Max: {max(score_vals):.3f}"
        )
    print("\nISSUES")
    if issues:
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("  (none)")
    print("\nWARNINGS")
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("  (none)")

    report_lines = [
        "# Scribe-IQ Corpus Audit Report\n",
        "## Scale\n",
        f"| Patients | {len(patients)} |\n",
        f"| Encounters | {len(encounters)} |\n",
        f"| Notes | {len(notes)} |\n",
        f"| Dialogues | {len(dialogues)} |\n",
        "## Showcase\n",
        f"| Total showcase | {len(showcase_enc_ids)} |\n",
        f"| With ACI dialogue | {len(showcase_aci_dlg)} |\n",
        f"| With any dialogue | {len(showcase_with_dlg)} |\n",
        f"| No dialogue | {len(showcase_no_dlg)} |\n",
        "## Issues\n",
        "None\n" if not issues else "\n".join(f"- {i}" for i in issues) + "\n",
        "## Warnings\n",
        "None\n" if not warnings else "\n".join(f"- {w}" for w in warnings) + "\n",
    ]
    (CORPUS / "audit_report.md").write_text("".join(report_lines), encoding="utf-8")
    print(f"\n✓ audit_report.md → {CORPUS}")


if __name__ == "__main__":
    main()
