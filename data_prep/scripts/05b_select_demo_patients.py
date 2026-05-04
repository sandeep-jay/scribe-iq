"""
05b_select_demo_patients.py — stratified demo cohort (run from data_prep/ or repo root).

Picks TARGET_TOTAL patients with:
  • encounter count (match rows) in [ENCOUNTER_MIN, ENCOUNTER_MAX]
  • mean match_score >= MIN_AVG_MATCH_SCORE (same gate as 05)
  • at least one row has non-empty conditions
  • quality_score (mean match) >= MIN_QUALITY_SCORE (default 0.80)

Spreads specialties via round-robin over shuffled specialty buckets (best-first within each).

Output: data/staging/selected_patients_demo.jsonl (same rows as 05).

Downstream: export SCRIBE_SELECTED_PATIENTS_JSONL=data/staging/selected_patients_demo.jsonl
before 06–07, or merge into your workflow.
"""
from __future__ import annotations

import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))

from pathlib import Path

from utils.io_utils import load_jsonl, write_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
MATCH_RESULTS = REPO_ROOT / "data/staging/match_results.jsonl"
OUTPUT = REPO_ROOT / "data/staging/selected_patients_demo.jsonl"

TARGET_TOTAL = int(os.environ.get("DEMO_TARGET_TOTAL", "20"))
ENCOUNTER_MIN = int(os.environ.get("DEMO_ENCOUNTER_MIN", "21"))
ENCOUNTER_MAX = int(os.environ.get("DEMO_ENCOUNTER_MAX", "39"))
MIN_AVG_MATCH_SCORE = float(os.environ.get("DEMO_MIN_AVG_MATCH_SCORE", "0.35"))
MIN_QUALITY_SCORE = float(os.environ.get("DEMO_MIN_QUALITY_SCORE", "0.80"))
MIN_ENCOUNTERS = int(os.environ.get("DEMO_MIN_ENCOUNTERS", "3"))
RANDOM_SEED = int(os.environ.get("DEMO_RANDOM_SEED", "42"))


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)

    patient_data: dict[str, dict] = defaultdict(
        lambda: {"encounters": [], "scores": [], "specialties": []}
    )
    for r in load_jsonl(MATCH_RESULTS):
        pid = r["patient_id"]
        patient_data[pid]["encounters"].append(r)
        patient_data[pid]["scores"].append(r["match_score"])
        patient_data[pid]["specialties"].append(r["specialty"])

    scored: list[dict] = []
    for pid, data in patient_data.items():
        n_enc = len(data["encounters"])
        if n_enc < MIN_ENCOUNTERS:
            continue
        if not (ENCOUNTER_MIN <= n_enc <= ENCOUNTER_MAX):
            continue
        avg_score = sum(data["scores"]) / len(data["scores"])
        if avg_score < MIN_AVG_MATCH_SCORE:
            continue
        if avg_score < MIN_QUALITY_SCORE:
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

    by_spec: dict[str, list[dict]] = defaultdict(list)
    for row in scored:
        by_spec[row["primary_specialty"]].append(row)

    for lst in by_spec.values():
        lst.sort(key=lambda x: (-x["quality_score"], x["patient_id"]))

    specs = list(by_spec.keys())
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(specs)

    pointers: dict[str, int] = {s: 0 for s in specs}
    selected: list[dict] = []
    while len(selected) < TARGET_TOTAL:
        progressed = False
        for s in specs:
            if len(selected) >= TARGET_TOTAL:
                break
            lst = by_spec[s]
            i = pointers[s]
            if i < len(lst):
                selected.append(lst[i])
                pointers[s] = i + 1
                progressed = True
        if not progressed:
            break

    for row in selected:
        write_jsonl(OUTPUT, row)

    dist = Counter(p["primary_specialty"] for p in selected)
    print(f"\n✓ Demo selection: {len(selected)} / {TARGET_TOTAL} patients (pool after filters: {len(scored)})")
    print(f"  Encounter band: [{ENCOUNTER_MIN}, {ENCOUNTER_MAX}], quality_score >= {MIN_QUALITY_SCORE}")
    print("\nSpecialty distribution:")
    for spec, count in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {spec:<30} {count}")
    qs = [p["quality_score"] for p in selected]
    if qs:
        print(f"\nQuality score range: {min(qs):.3f} – {max(qs):.3f}")
    enc = [p["encounter_count"] for p in selected]
    if enc:
        print(f"Encounter count range: {min(enc)} – {max(enc)}")
    print(f"\nOutput: {OUTPUT}")
    print(
        "\nNext: export SCRIBE_SELECTED_PATIENTS_JSONL="
        "data/staging/selected_patients_demo.jsonl\n"
        "then run 06 → 07 (from repo root or data_prep/)."
    )


if __name__ == "__main__":
    main()
