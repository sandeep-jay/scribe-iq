#!/usr/bin/env python3
"""
Phase 2 — Table-specific seed plan from staged Parquet (no LLM, no Postgres).

Reads data/staging/manifest.json and the Parquet path inside it; writes:
  - data/staging/phase1_seed_plan.json
  - data/staging/patient_assignments.jsonl
  - data/staging/selected_note_records.jsonl

Usage:
  cd corpus_pipelines/agbonnet_hf_clinical_notes && source .venv/bin/activate && pip install -r requirements.txt
  python scripts/create_seed_plan.py
  python scripts/create_seed_plan.py --seed 42 --manifest ../data/staging/manifest.json

See docs/archive/PHASE1_MASTER_PLAN.md §4.6 and corpus_pipelines/agbonnet_hf_clinical_notes/README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

# scripts/ on path for optional shared constants
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _balanced_specialties(n_patients: int, specialties: list[str], rng) -> list[str]:
    """Assign exactly n_patients specialties as evenly as possible, then shuffle order."""
    k = len(specialties)
    base, extra = divmod(n_patients, k)
    counts = [base] * k
    for i in range(extra):
        counts[i] += 1
    out: list[str] = []
    for spec, c in zip(specialties, counts, strict=True):
        out.extend([spec] * c)
    assert len(out) == n_patients
    rng.shuffle(out)
    return out


def _json_val(v: Any) -> Any:
    """Convert pandas/NaN to JSON-serializable."""
    if v is None:
        return None
    if isinstance(v, float) and __import__("math").isnan(v):
        return None
    try:
        if pd.isna(v):
            return None
    except TypeError:
        pass
    return v


def _random_dates_unique(rng, n: int, start: date, end: date) -> list[date]:
    """n unique random dates in [start, end]."""
    span = (end - start).days + 1
    if n > span:
        raise ValueError(f"Need {n} unique dates but range has only {span} days")
    picks = set()
    while len(picks) < n:
        off = rng.randint(0, span - 1)
        picks.add(start + timedelta(days=off))
    return sorted(picks)


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 2 — build application seed plan JSON/JSONL from staged Parquet.")
    ap.add_argument("--repo-root", type=Path, default=None, help="Repo root (default: inferred from script location)")
    ap.add_argument("--manifest", type=Path, default=None, help="Path to manifest.json (default: <repo>/data/staging/manifest.json)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--target-notes", type=int, default=400)
    ap.add_argument("--target-patients", type=int, default=50)
    ap.add_argument("--notes-per-patient", type=int, default=8)
    ap.add_argument("--min-conversation-chars", type=int, default=400, help="Drop if conversation shorter than this")
    ap.add_argument("--max-conversation-chars", type=int, default=24_000)
    ap.add_argument("--min-reference-note-chars", type=int, default=400, help="Drop if reference note shorter than this")
    ap.add_argument("--max-reference-note-chars", type=int, default=32_000)
    ap.add_argument(
        "--specialties",
        default="cardiology,endocrinology,pulmonology,neurology",
        help="Comma-separated synthetic specialty labels",
    )
    args = ap.parse_args()

    repo = args.repo_root or _repo_root()
    manifest_path = args.manifest or (repo / "data" / "staging" / "manifest.json")
    if not manifest_path.is_file():
        print(f"BLOCKER: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cols_meta = manifest.get("canonical_columns") or {}
    conv_col = cols_meta.get("transcript_column") or "conversation"
    note_col = cols_meta.get("reference_note_column") or "note"
    full_col = cols_meta.get("full_note_column") or "full_note"
    summ_col = cols_meta.get("summary_json_column") or "summary"
    idx_col = "idx"

    split = next(iter(manifest["splits"]))
    rel = manifest["splits"][split]["parquet_relative"]
    parquet_path = repo / rel
    if not parquet_path.is_file():
        print(f"BLOCKER: parquet not found: {parquet_path}", file=sys.stderr)
        return 1

    specs = [s.strip() for s in args.specialties.split(",") if s.strip()]
    if len(specs) < 1:
        print("BLOCKER: need at least one specialty", file=sys.stderr)
        return 1

    if args.target_notes != args.target_patients * args.notes_per_patient:
        print(
            "BLOCKER: target-notes must equal target-patients * notes-per-patient",
            file=sys.stderr,
        )
        return 1

    rng = __import__("random").Random(args.seed)

    df = pq.read_table(parquet_path).to_pandas()
    staged_total = len(df)

    needed_cols = [c for c in [idx_col, conv_col, note_col, full_col, summ_col] if c in df.columns]
    for c in (idx_col, conv_col, note_col):
        if c not in df.columns:
            print(f"BLOCKER: column {c!r} missing from parquet", file=sys.stderr)
            return 1

    exclusions: dict[str, int] = {
        "missing_conversation": 0,
        "missing_reference_note": 0,
        "short_conversation": 0,
        "long_conversation": 0,
        "short_reference_note": 0,
        "long_reference_note": 0,
        "duplicate_conversation": 0,
    }
    seen_hashes: set[str] = set()
    keep_mask = []

    for _, row in df.iterrows():
        conv = row[conv_col]
        note = row[note_col]
        conv_s = conv if isinstance(conv, str) else ("" if conv is None or (isinstance(conv, float) and pd.isna(conv)) else str(conv))
        note_s = note if isinstance(note, str) else ("" if note is None or (isinstance(note, float) and pd.isna(note)) else str(note))
        conv_s = conv_s.strip()
        note_s = note_s.strip()

        if not conv_s:
            exclusions["missing_conversation"] += 1
            keep_mask.append(False)
            continue
        if not note_s:
            exclusions["missing_reference_note"] += 1
            keep_mask.append(False)
            continue
        if len(conv_s) < args.min_conversation_chars:
            exclusions["short_conversation"] += 1
            keep_mask.append(False)
            continue
        if len(conv_s) > args.max_conversation_chars:
            exclusions["long_conversation"] += 1
            keep_mask.append(False)
            continue
        if len(note_s) < args.min_reference_note_chars:
            exclusions["short_reference_note"] += 1
            keep_mask.append(False)
            continue
        if len(note_s) > args.max_reference_note_chars:
            exclusions["long_reference_note"] += 1
            keep_mask.append(False)
            continue

        h = _sha256(_normalize_text(conv_s))
        if h in seen_hashes:
            exclusions["duplicate_conversation"] += 1
            keep_mask.append(False)
            continue
        seen_hashes.add(h)
        keep_mask.append(True)

    clean = df.loc[keep_mask].reset_index(drop=True)
    after_filters = len(clean)

    if after_filters < args.target_notes:
        print(
            f"BLOCKER: only {after_filters} clean rows (need {args.target_notes}). "
            f"Relax min/max lengths or dedupe strategy.",
            file=sys.stderr,
        )
        return 1

    clean = clean.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)
    selected = clean.iloc[: args.target_notes].copy()
    selected_count = len(selected)

    specialties_assign = _balanced_specialties(args.target_patients, specs, rng)

    patients: list[dict[str, Any]] = []
    note_rows_out: list[dict[str, Any]] = []

    start_d = date(2024, 1, 1)
    end_d = date(2025, 12, 31)

    for pidx in range(args.target_patients):
        spec = specialties_assign[pidx]
        age = rng.randint(25, 88)
        sex = rng.choice(["M", "F"])
        patient_uuid = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"scribe-iq:seed={args.seed}:patient={pidx}")
        )
        display_name = f"Synthetic Patient {pidx + 1:03d}"

        slice_df = selected.iloc[pidx * args.notes_per_patient : (pidx + 1) * args.notes_per_patient]
        dates = _random_dates_unique(rng, args.notes_per_patient, start_d, end_d)

        note_meta: list[dict[str, Any]] = []
        for j, (_, srow) in enumerate(slice_df.iterrows()):
            session_date = dates[j].isoformat()
            ds_idx = str(srow[idx_col])
            rec = {
                "patient_id": patient_uuid,
                "patient_index": pidx,
                "session_date": session_date,
                "dataset_split": split,
                "dataset_idx": ds_idx,
                "conversation": _json_val(srow[conv_col]),
                "reference_note": _json_val(srow[note_col]),
                "full_note": _json_val(srow[full_col]) if full_col in srow.index else None,
                "summary_json": _json_val(srow[summ_col]) if summ_col in srow.index else None,
            }
            note_rows_out.append(rec)
            note_meta.append({"dataset_idx": ds_idx, "session_date": session_date})

        patients.append(
            {
                "patient_id": patient_uuid,
                "patient_index": pidx,
                "display_name": display_name,
                "specialty": spec,
                "age": age,
                "sex": sex,
                "notes": note_meta,
            }
        )

    spec_dist = dict(Counter(specialties_assign))

    out_dir = repo / "data" / "staging"
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "phase1_seed_plan.json"
    assign_path = out_dir / "patient_assignments.jsonl"
    notes_path = out_dir / "selected_note_records.jsonl"

    plan = {
        "schema_version": 1,
        "phase": "2",
        "step": "P2-seed",
        "description": "Deterministic seed plan for Phase 3 DB load (no LLM).",
        "random_seed": args.seed,
        "manifest_path": str(manifest_path.relative_to(repo)),
        "parquet_path": str(parquet_path.relative_to(repo)),
        "canonical_columns": {
            "conversation": conv_col,
            "reference_note": note_col,
            "full_note": full_col,
            "summary_json": summ_col,
            "dataset_idx": idx_col,
        },
        "thresholds": {
            "min_conversation_chars": args.min_conversation_chars,
            "max_conversation_chars": args.max_conversation_chars,
            "min_reference_note_chars": args.min_reference_note_chars,
            "max_reference_note_chars": args.max_reference_note_chars,
        },
        "exclusion_counts": exclusions,
        "row_counts": {
            "staged_total": staged_total,
            "after_filters": int(after_filters),
            "selected_notes": int(selected_count),
            "patients": args.target_patients,
            "notes_per_patient": args.notes_per_patient,
        },
        "specialty_distribution": spec_dist,
        "session_date_range": {"start": start_d.isoformat(), "end": end_d.isoformat()},
        "outputs": {
            "phase1_seed_plan": str(plan_path.relative_to(repo)),
            "patient_assignments": str(assign_path.relative_to(repo)),
            "selected_note_records": str(notes_path.relative_to(repo)),
        },
    }

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    with assign_path.open("w", encoding="utf-8") as f:
        for p in patients:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with notes_path.open("w", encoding="utf-8") as f:
        for r in note_rows_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {plan_path.relative_to(repo)}")
    print(f"Wrote {assign_path.relative_to(repo)} ({len(patients)} lines)")
    print(f"Wrote {notes_path.relative_to(repo)} ({len(note_rows_out)} lines)")
    print("Phase 2 seed plan complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
