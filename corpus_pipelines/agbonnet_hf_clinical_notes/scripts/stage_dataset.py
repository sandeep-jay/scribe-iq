#!/usr/bin/env python3
"""Download HF split(s) to repo-local Parquet + manifest (Phase 0 staging).

No database, no FastAPI. Output is consumed later by Phase 1 `load_clinical_data.py`.

Usage:
    cd corpus_pipelines/agbonnet_hf_clinical_notes && source .venv/bin/activate && pip install -r requirements.txt
    python scripts/stage_dataset.py

See docs/archive/PHASE1_MASTER_PLAN.md §4.4.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/stage_dataset.py` without installing the package
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import argparse
import json
import re
from datetime import UTC, datetime
from typing import Any

from datasets import Dataset, DatasetDict, load_dataset

from corpus_constants import (
    CANONICAL_FULL_NOTE_COLUMN,
    CANONICAL_REFERENCE_NOTE_COLUMN,
    CANONICAL_SUMMARY_JSON_COLUMN,
    CANONICAL_TRANSCRIPT_COLUMN,
    DEFAULT_DATASET_ID,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _slug_dataset_id(dataset_id: str) -> str:
    s = dataset_id.replace("/", "__")
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def _ci_map(columns: list[str]) -> dict[str, str]:
    return {c.lower(): c for c in columns}


def _recommend_canonical(columns: list[str]) -> dict[str, str | None]:
    m = _ci_map(columns)
    trans = (
        CANONICAL_TRANSCRIPT_COLUMN
        if CANONICAL_TRANSCRIPT_COLUMN.lower() in m
        else next((m[t] for t in ("conversation", "transcript", "dialogue", "text") if t in m), None)
    )
    note = (
        CANONICAL_REFERENCE_NOTE_COLUMN
        if CANONICAL_REFERENCE_NOTE_COLUMN.lower() in m
        else next((m[t] for t in ("note", "clinical_note", "output") if t in m), None)
    )
    fulln = m.get(CANONICAL_FULL_NOTE_COLUMN.lower())
    summ = m.get(CANONICAL_SUMMARY_JSON_COLUMN.lower())
    return {
        "transcript_column": trans,
        "reference_note_column": note,
        "full_note_column": fulln,
        "summary_json_column": summ,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage HF dataset to data/staging (Phase 0).")
    ap.add_argument("--dataset", default=DEFAULT_DATASET_ID)
    ap.add_argument("--revision", default=None, help="HF dataset git revision (pin reproducibility)")
    ap.add_argument("--output-dir", default=None, help="Staging root (default: <repo>/data/staging)")
    ap.add_argument("--trust-remote-code", action="store_true")
    args = ap.parse_args()

    out_root = Path(args.output_dir) if args.output_dir else _repo_root() / "data" / "staging"
    slug = _slug_dataset_id(args.dataset)
    bundle_dir = out_root / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    kw: dict[str, Any] = {}
    if args.revision:
        kw["revision"] = args.revision
    if args.trust_remote_code:
        kw["trust_remote_code"] = True

    print(f"Loading {args.dataset!r} …")
    try:
        raw = load_dataset(args.dataset, **kw)
    except Exception as e:
        print(f"BLOCKER: load_dataset failed: {e}", file=sys.stderr)
        return 1

    split_paths: dict[str, str] = {}
    split_rows: dict[str, int] = {}
    columns: list[str] = []

    if isinstance(raw, DatasetDict):
        items = list(raw.items())
    elif isinstance(raw, Dataset):
        items = [("train", raw)]
    else:
        print(f"BLOCKER: unexpected type {type(raw)}", file=sys.stderr)
        return 1

    for split_name, ds in items:
        columns = ds.column_names
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", split_name)
        parquet_path = bundle_dir / f"{safe}.parquet"
        print(f"  Writing {split_name!r} ({len(ds):,} rows) → {parquet_path}")
        ds.to_parquet(str(parquet_path))
        split_paths[split_name] = str(parquet_path.relative_to(_repo_root()))
        split_rows[split_name] = len(ds)

    rec = _recommend_canonical(columns)
    if not rec["transcript_column"]:
        print("BLOCKER: no transcript column detected.", file=sys.stderr)
        return 1

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "dataset_id": args.dataset,
        "revision": args.revision,
        "splits": {k: {"rows": split_rows[k], "parquet_relative": split_paths[k]} for k in split_paths},
        "columns": columns,
        "canonical_columns": rec,
        "notes": [
            "Phase 1 loader should read manifest + parquet under data/staging/.",
            "No specialty column in this corpus; assign synthetic specialty or derive in loader.",
        ],
    }
    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest → {manifest_path.relative_to(_repo_root())}")
    print("Phase 0 staging complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
