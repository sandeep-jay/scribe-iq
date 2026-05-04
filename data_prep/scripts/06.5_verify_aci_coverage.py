"""
06.5_verify_aci_coverage.py — run from data_prep/

Verifies dialogue coverage for showcase visits (last encounter per selected patient).
Uses aci_reservations.jsonl from script 03.

Env:
  SCRIBE_SELECTED_PATIENTS_JSONL
  SCRIBE_MATCH_RESULTS_JSONL
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _selected_patients_path() -> Path:
    override = os.environ.get("SCRIBE_SELECTED_PATIENTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    golden = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
    if golden.is_file():
        return golden
    return REPO_ROOT / "data/staging/selected_patients.jsonl"

def _match_results_path() -> Path:
    override = os.environ.get("SCRIBE_MATCH_RESULTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    golden = REPO_ROOT / "data/staging/match_results_golden.jsonl"
    if golden.is_file():
        return golden
    return REPO_ROOT / "data/staging/match_results.jsonl"

def main() -> None:
    golden_path = _selected_patients_path()
    matches_path = _match_results_path()
    aci_path = REPO_ROOT / "data/staging/aci_reservations.jsonl"

    if not golden_path.exists():
        raise SystemExit(f"Selected patients not found: {golden_path}")
    if not matches_path.exists():
        raise SystemExit(f"Match results not found: {matches_path}")

    cohort = [
        json.loads(line)
        for line in golden_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    golden_ids = [p["patient_id"] for p in cohort]
    id_set = set(golden_ids)

    by_patient: dict[str, list] = defaultdict(list)
    for line in matches_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        m = json.loads(line)
        if m["patient_id"] in id_set:
            by_patient[m["patient_id"]].append(m)

    def sort_key(row: dict) -> tuple:
        return (row["encounter_date"], row["encounter_id"])

    showcase_encounters: dict[str, dict] = {}
    for pid in golden_ids:
        encs = sorted(by_patient.get(pid, []), key=sort_key)
        if not encs:
            continue
        showcase_encounters[pid] = encs[-1]

    aci_reserved: dict[str, dict] = {}
    if aci_path.exists():
        for line in aci_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            aci_reserved[r["note_id"]] = r
    else:
        print(f"⚠️  {aci_path} not found — run 03_reserve_aci_encounters.py first")

    labels = []
    for pid in golden_ids:
        sh = showcase_encounters.get(pid)
        if not sh:
            labels.append("no_encounters")
            continue
        nid = sh.get("best_note_id")
        if nid and nid in aci_reserved:
            labels.append("aci_bench_reserved")
        elif sh.get("best_note_dialogue"):
            src = (sh.get("best_note_source") or "unknown").strip()
            labels.append(f"dialogue_non_aci:{src}")
        else:
            labels.append("no_dialogue")

    ctr = Counter(labels)
    n = len(golden_ids)
    print("=" * 60)
    print("SHOWCASE DIALOGUE COVERAGE (last encounter per patient)")
    print("=" * 60)
    print(f"Cohort: {n} patients | matches: {matches_path.name}")
    for k in sorted(ctr.keys()):
        print(f"  {k}: {ctr[k]}")
    aci_n = ctr.get("aci_bench_reserved", 0)
    dlg_n = sum(v for k, v in ctr.items() if k.startswith("dialogue_non_aci:"))
    ok = aci_n + dlg_n
    print(f"\nWith dialogue (any source): {ok}/{n} ({100.0 * ok / n:.0f}%)")


if __name__ == "__main__":
    main()
