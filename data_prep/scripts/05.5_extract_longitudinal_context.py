"""
05.5_extract_longitudinal_context.py — run from data_prep/

Builds patient_longitudinal_context.jsonl: for each encounter in the selected
cohort, the last K prior visits as structured blocks (deterministic sort:
encounter_date, then encounter_id).

Env:
  SCRIBE_SELECTED_PATIENTS_JSONL (default data/staging/selected_patients.jsonl)
  SCRIBE_MATCH_RESULTS_JSONL (default data/staging/match_results.jsonl)
  SCRIBE_PRIOR_VISITS — int, default 6
  SCRIBE_LONGITUDINAL_CONTEXT_JSONL — output (default data/staging/patient_longitudinal_context.jsonl)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

_DP_ROOT = Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))

from utils.io_utils import load_jsonl, write_jsonl  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _selected_patients_path() -> Path:
    override = os.environ.get("SCRIBE_SELECTED_PATIENTS_JSONL", "").strip()
    if not override:
        return REPO_ROOT / "data/staging/selected_patients.jsonl"
    p = Path(override)
    return p if p.is_absolute() else REPO_ROOT / p


def _match_results_path() -> Path:
    override = os.environ.get("SCRIBE_MATCH_RESULTS_JSONL", "").strip()
    if not override:
        return REPO_ROOT / "data/staging/match_results.jsonl"
    p = Path(override)
    return p if p.is_absolute() else REPO_ROOT / p


def _output_path() -> Path:
    override = os.environ.get("SCRIBE_LONGITUDINAL_CONTEXT_JSONL", "").strip()
    if not override:
        return REPO_ROOT / "data/staging/patient_longitudinal_context.jsonl"
    p = Path(override)
    return p if p.is_absolute() else REPO_ROOT / p


def _prior_visits_k() -> int:
    raw = os.environ.get("SCRIBE_PRIOR_VISITS", "").strip()
    if not raw:
        return 6
    try:
        k = int(raw, 10)
        return max(0, k)
    except ValueError:
        return 6


def sanitize_string(value, default: str = "Not documented") -> str:
    if value is None or (isinstance(value, float) and value != value):
        return default
    s = str(value).strip()
    return s if s else default



def _uniq_labels(rows: list) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in rows:
        lab = str(raw).strip()
        if not lab or lab in seen:
            continue
        seen.add(lab)
        out.append(lab)
    return out


def _obs_lines(obs_list: list, limit: int = 3) -> list[str]:
    lines = []
    for o in (obs_list or [])[:limit]:
        lines.append(
            f"{o.get('DESCRIPTION', 'Unknown')}: {o.get('VALUE', '')} {o.get('UNITS', '')}".strip()
        )
    return lines


def main() -> None:
    selected_path = _selected_patients_path()
    matches_path = _match_results_path()
    output_path = _output_path()
    k_pri = _prior_visits_k()

    if not selected_path.exists():
        raise SystemExit(f"Selected patients not found: {selected_path}")
    if not matches_path.exists():
        raise SystemExit(f"Match results not found: {matches_path}")

    cohort = [
        json.loads(line)
        for line in selected_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cohort_ids = [p["patient_id"] for p in cohort]
    cohort_set = set(cohort_ids)

    matches_by_patient: dict[str, list] = defaultdict(list)
    for m in load_jsonl(matches_path):
        if m["patient_id"] in cohort_set:
            matches_by_patient[m["patient_id"]].append(m)

    def sort_key(row: dict) -> tuple:
        return (row["encounter_date"], row["encounter_id"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)
    total = 0

    for pid in cohort_ids:
        encs = sorted(matches_by_patient.get(pid, []), key=sort_key)
        for i, current_enc in enumerate(encs):
            prior_start = max(0, i - k_pri)
            prior_encs = encs[prior_start:i]
            prior_blocks = []
            for prior in prior_encs:
                prior_blocks.append(
                    {
                        "encounter_id": prior["encounter_id"],
                        "date": prior["encounter_date"][:10],
                        "reason": sanitize_string(prior.get("encounter_reason")),
                        "conditions": list(prior.get("conditions", [])[:5]),
                        "medications": list(prior.get("medications", [])[:5]),
                        "key_observations": _obs_lines(prior.get("recent_obs", []), 3),
                    }
                )
            cur_snapshot = {
                "encounter_id": current_enc["encounter_id"],
                "date": current_enc["encounter_date"][:10],
                "reason": sanitize_string(current_enc.get("encounter_reason")),
                "conditions": list((current_enc.get("conditions") or [])[:12]),
                "medications": list((current_enc.get("medications") or [])[:25]),
            }

            meds_union = _uniq_labels(
                [*cur_snapshot["medications"], *[m for b in prior_blocks for m in b.get("medications", [])]]
            )

            write_jsonl(
                output_path,
                {
                    "patient_id": pid,
                    "encounter_id": current_enc["encounter_id"],
                    "encounter_date": current_enc["encounter_date"],
                    "current_encounter_snapshot": cur_snapshot,
                    "medications_union": meds_union,
                    "prior_visits": prior_blocks,
                    "num_prior_visits": len(prior_blocks),
                },
            )
            total += 1

    print(f"✓ Longitudinal context: {total} records → {output_path}")


if __name__ == "__main__":
    main()
