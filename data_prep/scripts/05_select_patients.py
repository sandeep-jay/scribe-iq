"""
05_select_patients.py — run from data_prep/
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


from collections import Counter, defaultdict
from pathlib import Path

from utils.io_utils import load_jsonl, write_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
MATCH_RESULTS = REPO_ROOT / "data/staging/match_results.jsonl"
OUTPUT = REPO_ROOT / "data/staging/selected_patients.jsonl"

TARGET_TOTAL = 50
MAX_PER_SPECIALTY = 10
MAX_PER_GENERAL_MEDICINE = 50
MIN_ENCOUNTERS = 3
MIN_AVG_MATCH_SCORE = 0.35


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)

    results = list(load_jsonl(MATCH_RESULTS))
    patient_data = defaultdict(
        lambda: {"encounters": [], "scores": [], "specialties": []}
    )
    for r in results:
        pid = r["patient_id"]
        patient_data[pid]["encounters"].append(r)
        patient_data[pid]["scores"].append(r["match_score"])
        patient_data[pid]["specialties"].append(r["specialty"])

    scored = []
    for pid, data in patient_data.items():
        n_enc = len(data["encounters"])
        avg_score = sum(data["scores"]) / len(data["scores"])
        if n_enc < MIN_ENCOUNTERS:
            continue
        if avg_score < MIN_AVG_MATCH_SCORE:
            continue
        if not any(r.get("conditions") for r in data["encounters"]):
            continue
        primary = Counter(data["specialties"]).most_common(1)[0][0]
        scored.append(
            {
                "patient_id": pid,
                "quality_score": round(avg_score, 3),
                "encounter_count": n_enc,
                "primary_specialty": primary,
            }
        )

    scored.sort(key=lambda x: x["quality_score"], reverse=True)

    selected = []
    spec_counts = defaultdict(int)
    for patient in scored:
        spec = patient["primary_specialty"]
        cap = (
            MAX_PER_GENERAL_MEDICINE
            if spec == "General Medicine"
            else MAX_PER_SPECIALTY
        )
        if spec_counts[spec] >= cap:
            continue
        selected.append(patient)
        spec_counts[spec] += 1
        if len(selected) >= TARGET_TOTAL:
            break

    for row in selected:
        write_jsonl(OUTPUT, row)

    print(f"\n✓ Selected {len(selected)} patients")
    print("\nSpecialty distribution:")
    for spec, count in sorted(spec_counts.items(), key=lambda x: -x[1]):
        print(f"  {spec:<30} {count}")
    qs = [p["quality_score"] for p in selected]
    if qs:
        print(f"\nQuality score range: {min(qs):.3f} – {max(qs):.3f}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
