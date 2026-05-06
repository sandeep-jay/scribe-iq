#!/usr/bin/env python3
"""
Export staged corpus Parquet (from manifest) to JSONL under data/staging/.

One JSON object per line; UTF-8. Reuses the Parquet row order. No DB / Azure.

Usage (repo root):
    python corpus_pipelines/agbonnet_hf_clinical_notes/scripts/export_staged_parquet_jsonl.py

See corpus_pipelines/agbonnet_hf_clinical_notes/README.md.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _json_val(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    try:
        if pd.isna(v):
            return None
    except TypeError:
        pass
    if hasattr(v, "item") and callable(getattr(v, "item")):
        try:
            return v.item()
        except (ValueError, AttributeError):
            pass
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description="Export staged Parquet to JSONL (manifest-driven).")
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument(
        "--split",
        type=str,
        default=None,
        help="Split name in manifest (default: first split)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSONL path (repo-relative; default: same dir as Parquet, .jsonl)",
    )
    ap.add_argument("--batch-rows", type=int, default=512, help="Parquet batch size for streaming")
    ap.add_argument("--limit", type=int, default=None, help="Max rows to write (after read order)")
    args = ap.parse_args()

    repo = args.repo_root.resolve() if args.repo_root else _repo_root()
    manifest_path = args.manifest or (repo / "data" / "staging" / "manifest.json")
    if not manifest_path.is_file():
        print(f"BLOCKER: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    splits = manifest.get("splits") or {}
    if not splits:
        print("BLOCKER: manifest has no splits", file=sys.stderr)
        return 1

    split_name = args.split if args.split else next(iter(splits))
    if split_name not in splits:
        print(f"BLOCKER: split {split_name!r} not in manifest", file=sys.stderr)
        return 1

    rel = splits[split_name]["parquet_relative"]
    parquet_path = repo / rel
    if not parquet_path.is_file():
        print(f"BLOCKER: parquet not found: {parquet_path}", file=sys.stderr)
        return 1

    if args.out:
        out_path = args.out if args.out.is_absolute() else (repo / args.out)
    else:
        out_path = parquet_path.with_suffix(".jsonl")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    pf = pq.ParquetFile(parquet_path)
    batch_rows = max(1, args.batch_rows)

    with out_path.open("w", encoding="utf-8") as f:
        for batch in pf.iter_batches(batch_size=batch_rows):
            df = batch.to_pandas()
            for rec in df.to_dict(orient="records"):
                if args.limit is not None and written >= args.limit:
                    break
                clean = {k: _json_val(v) for k, v in rec.items()}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")
                written += 1
            if args.limit is not None and written >= args.limit:
                break

    print(f"Wrote {out_path.relative_to(repo)} ({written} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
