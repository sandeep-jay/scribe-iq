#!/usr/bin/env python3
"""Task 0 — Inspect Hugging Face dataset before Phase 1 (Phase 0).

Usage:
    cd lakehouse
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/validate_dataset.py

If ~/.cache/huggingface is not writable (e.g. sandbox), use a repo-local cache:
    export HF_HOME="$(pwd)/.hf_home"
    mkdir -p "$HF_HOME"

See roadmap/PHASE1_MASTER_PLAN.md §4.3 (Phase 0).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from datasets import Dataset, DatasetDict, load_dataset

TRANSCRIPT_NAMES = ("conversation", "transcript", "dialogue", "text")
NOTE_NAMES = ("note", "clinical_note", "output", "summary")
EXPECTED_OPTIONAL = ("conversation", "note", "summary")
SPECIALTY_SUBSTRINGS = (
    "specialty", "category", "department", "discipline", "clinical_specialty",
)


def _truncate(s: str, max_chars: int) -> str:
    return s if len(s) <= max_chars else s[: max_chars - 3] + "..."


def _is_nullish(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and not v.strip()


def _as_printable(v: Any, max_chars: int) -> str:
    if v is None:
        return "null"
    if isinstance(v, str):
        return _truncate(json.dumps(v), max_chars)
    if isinstance(v, (bytes, bytearray)):
        raw = bytes(v[:200]).decode("utf-8", errors="replace")
        return _truncate(json.dumps(raw), max_chars)
    if isinstance(v, Mapping):
        return _truncate(json.dumps(v, default=str, ensure_ascii=False), max_chars)
    if isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray)):
        short = list(v)[:30]
        return _truncate(json.dumps(short, default=str, ensure_ascii=False), max_chars)
    return _truncate(repr(v), max_chars)


def _ci_map(columns: list[str]) -> dict[str, str]:
    return {c.lower(): c for c in columns}


def _find_names(columns: list[str], names: tuple[str, ...]) -> list[str]:
    m = _ci_map(columns)
    return list(dict.fromkeys(m[n.lower()] for n in names if n.lower() in m))


def _specialty_cols(columns: list[str]) -> list[str]:
    return [c for c in columns if any(h in c.lower() for h in SPECIALTY_SUBSTRINGS)]


def _text_lengths_sample(ds: Dataset, col: str, cap: int) -> list[int]:
    n = min(len(ds), cap)
    out: list[int] = []
    for i in range(n):
        v = ds[i][col]
        if isinstance(v, str):
            out.append(len(v))
        elif v is None:
            out.append(0)
        else:
            out.append(len(json.dumps(v, default=str)))
    return out


def _stats(xs: list[int]) -> dict[str, float]:
    if not xs:
        return {}
    xs_sorted = sorted(xs)
    n = len(xs)

    def pct(p: float) -> int:
        if n == 1:
            return xs_sorted[0]
        k = (n - 1) * p
        lo = int(math.floor(k))
        hi = int(math.ceil(k))
        if lo == hi:
            return xs_sorted[lo]
        return int(xs_sorted[lo] + (xs_sorted[hi] - xs_sorted[lo]) * (k - lo))

    return {
        "n": float(n),
        "min": float(xs_sorted[0]),
        "max": float(xs_sorted[-1]),
        "mean": float(sum(xs_sorted) / n),
        "p50": float(pct(0.50)),
        "p95": float(pct(0.95)),
    }


def _null_counts(ds: Dataset, columns: list[str], cap: int) -> dict[str, int]:
    n = min(len(ds), cap)
    counts = {c: 0 for c in columns}
    for i in range(n):
        row = ds[i]
        for c in columns:
            if _is_nullish(row.get(c)):
                counts[c] += 1
    return counts


def _report_split(
    split_name: str,
    ds: Dataset,
    max_chars: int,
    null_cap: int,
    text_cap: int,
) -> None:
    cols = ds.column_names
    print(f"\n{'=' * 72}\nSplit: {split_name!r} — rows: {len(ds):,}\nColumns ({len(cols)}): {cols}")
    m = _ci_map(cols)
    print("\n-- Expected-name checks (case-insensitive exact) --")
    for name in EXPECTED_OPTIONAL:
        ok = name.lower() in m
        print(f"  {name!r} present: {ok}" + (f" → {m[name.lower()]}" if ok else ""))
    sp = _specialty_cols(cols)
    print(f"  specialty-like columns: {sp or 'none'}")
    tm = _find_names(cols, TRANSCRIPT_NAMES)
    nm = _find_names(cols, NOTE_NAMES)
    print("\n-- Heuristic transcript columns --\n  matched:", tm or "none")
    print("\n-- Heuristic note columns --\n  matched:", nm or "none")
    rec_t = next((m[t.lower()] for t in TRANSCRIPT_NAMES if t.lower() in m), None)
    rec_n = next((m[t.lower()] for t in ("note", "clinical_note", "output", "summary") if t.lower() in m), None)
    print("\n-- Recommended canonical fields --")
    print(f"  transcript: {rec_t or 'NONE — BLOCKER'}\n  reference_note (eval only): {rec_n or 'none'}")
    print(f"\n-- Null / empty counts (first {null_cap:,} rows) --")
    for c, k in _null_counts(ds, cols, null_cap).items():
        print(f"  {c!r}: {k:,}")
    skip_stats = {"idx", "id"}
    str_cols = [
        c
        for c in cols
        if len(ds) and isinstance(ds[0].get(c), str) and c.lower() not in skip_stats
    ]
    stats_cols = list(dict.fromkeys(tm + nm + str_cols))
    print(f"\n-- Text length stats (sample up to {text_cap:,}) --")
    for c in stats_cols:
        lens = _text_lengths_sample(ds, c, text_cap)
        if not lens:
            continue
        st = _stats(lens)
        print(
            f"  {c!r}: n={int(st['n'])} min={st['min']:.0f} max={st['max']:.0f} "
            f"mean={st['mean']:.1f} p50={st['p50']:.0f} p95={st['p95']:.0f}"
        )
    print("\n-- First 3 records (truncated) --")
    for i in range(min(3, len(ds))):
        row = ds[i]
        print(f"  --- row {i} ---")
        for k in cols:
            print(f"    {k}: {_as_printable(row[k], max_chars)}")


def _verdict(cols: list[str], splits: dict[str, int]) -> None:
    m = _ci_map(cols)
    ok_t = any(t.lower() in m for t in TRANSCRIPT_NAMES)
    print("\n" + "=" * 72 + "\nVERDICT\n" + "=" * 72)
    if not splits:
        print("BLOCKER: No splits / empty dataset.")
        return
    if not ok_t:
        print("BLOCKER: No transcript column in", TRANSCRIPT_NAMES)
        return
    print(
        "PROCEED: Transcript column found. Confirm mapping & specialty from samples before loader."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Task 0 — HF dataset inspection (Scribe IQ).")
    ap.add_argument("--dataset", default="AGBonnet/augmented-clinical-notes")
    ap.add_argument("--split", default=None)
    ap.add_argument("--revision", default=None)
    ap.add_argument("--max-chars", type=int, default=800)
    ap.add_argument("--null-sample-cap", type=int, default=50_000)
    ap.add_argument("--text-stats-sample", type=int, default=10_000)
    ap.add_argument("--trust-remote-code", action="store_true")
    args = ap.parse_args()

    print(f"Loading {args.dataset!r} …")
    kw: dict[str, Any] = {}
    if args.revision:
        kw["revision"] = args.revision
    if args.trust_remote_code:
        kw["trust_remote_code"] = True
    try:
        raw = load_dataset(args.dataset, split=args.split, **kw)
    except Exception as e:
        print(f"\nBLOCKER: load_dataset failed: {e}", file=sys.stderr)
        if "trust_remote_code" in str(e).lower():
            print("Hint: --trust-remote-code", file=sys.stderr)
        return 1

    split_lengths: dict[str, int] = {}
    all_cols: list[str] = []

    if isinstance(raw, DatasetDict):
        print(f"\nDataset splits: {list(raw.keys())}")
        for sn, d in raw.items():
            split_lengths[sn] = len(d)
            all_cols = d.column_names
            _report_split(sn, d, args.max_chars, args.null_sample_cap, args.text_stats_sample)
    elif isinstance(raw, Dataset):
        sn = args.split or "single"
        split_lengths[sn] = len(raw)
        all_cols = raw.column_names
        print("\nSingle Dataset.")
        _report_split(sn, raw, args.max_chars, args.null_sample_cap, args.text_stats_sample)
    else:
        print(f"\nBLOCKER: bad type {type(raw)}")
        return 1

    print(f"\nRow counts: {{{', '.join(f'{k!r}: {split_lengths[k]}' for k in sorted(split_lengths))}}}")
    _verdict(all_cols, split_lengths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
