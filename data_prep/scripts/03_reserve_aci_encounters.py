"""
03_reserve_aci_encounters.py — run from data_prep/: python scripts/03_reserve_aci_encounters.py
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


from collections import defaultdict
from pathlib import Path

from utils.io_utils import load_jsonl, write_jsonl
from utils.mappings import specialty_from_clinical_text

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTE_POOL = REPO_ROOT / "data/staging/note_pool.jsonl"
OUTPUT = REPO_ROOT / "data/staging/aci_reservations.jsonl"
RESERVE_PER_SPECIALTY = 5


def classify_chief_complaint(cc: str) -> str:
    """Same keyword rules as 04 (word boundaries for single-token keys)."""
    return specialty_from_clinical_text(cc) or "General Medicine"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)

    aci_notes = [
        n
        for n in load_jsonl(NOTE_POOL)
        if n.get("source") == "aci_bench" and n.get("dialogue")
    ]
    print(f"ACI-Bench encounters with dialogue: {len(aci_notes)}")

    specialty_buckets: dict[str, list] = defaultdict(list)
    for note in aci_notes:
        spec = classify_chief_complaint(note.get("chief_complaint", ""))
        note = dict(note)
        note["specialty"] = spec
        specialty_buckets[spec].append(note)

    print("\nACI-Bench specialty distribution:")
    for spec, notes in sorted(specialty_buckets.items(), key=lambda x: -len(x[1])):
        print(f"  {spec:<30} {len(notes)}")

    used: set[str] = set()
    written = 0
    for _spec, notes in specialty_buckets.items():
        count = 0
        for note in notes:
            if count >= RESERVE_PER_SPECIALTY:
                break
            nid = note["note_id"]
            if nid in used:
                continue
            write_jsonl(
                OUTPUT,
                {
                    "note_id": nid,
                    "specialty": note["specialty"],
                    "chief_complaint": note.get("chief_complaint", ""),
                    "gender": note.get("gender", ""),
                    "note_text": note["note_text"],
                    "dialogue": note["dialogue"],
                    "reserved_for": note["specialty"],
                },
            )
            used.add(nid)
            count += 1
            written += 1

    if written == 0:
        OUTPUT.write_text("", encoding="utf-8")

    n_lines = sum(1 for _ in load_jsonl(OUTPUT)) if OUTPUT.exists() else 0
    print(f"\n✓ Reserved {n_lines} ACI encounters → {OUTPUT}")


if __name__ == "__main__":
    main()
