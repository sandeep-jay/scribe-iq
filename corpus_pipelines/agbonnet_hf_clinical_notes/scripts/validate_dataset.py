#!/usr/bin/env python3
"""Task 0 — Inspect Hugging Face dataset before Phase 1 (Phase 0).

Usage:
    cd corpus_pipelines/agbonnet_hf_clinical_notes
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/validate_dataset.py

If ~/.cache/huggingface is not writable (e.g. sandbox), use a repo-local cache:
    export HF_HOME="$(pwd)/.hf_home"
    mkdir -p "$HF_HOME"

See docs/archive/PHASE1_MASTER_PLAN.md §4.3 (Phase 0).
Leveled logs go to stderr via logging.basicConfig (INFO by default, DEBUG with -v).
Sample rows in reports are truncated to avoid dumping full clinical notes into CI logs.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections.abc import Mapping, Sequence
from typing import Any

log = logging.getLogger(__name__)

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
    log.info(f"\n{'=' * 72}\nSplit: {split_name!r} — rows: {len(ds):,}\nColumns ({len(cols)}): {cols}")
    m = _ci_map(cols)
    log.info("\n-- Expected-name checks (case-insensitive exact) --")
    for name in EXPECTED_OPTIONAL:
        ok = name.lower() in m
        log.info(f"  {name!r} present: {ok}" + (f" → {m[name.lower()]}" if ok else ""))
    sp = _specialty_cols(cols)
    log.info(f"  specialty-like columns: {sp or 'none'}")
    tm = _find_names(cols, TRANSCRIPT_NAMES)
    nm = _find_names(cols, NOTE_NAMES)
    log.info("\n-- Heuristic transcript columns --\n  matched: %s", tm or "none")
    log.info("\n-- Heuristic note columns --\n  matched: %s", nm or "none")
    rec_t = next((m[t.lower()] for t in TRANSCRIPT_NAMES if t.lower() in m), None)
    rec_n = next((m[t.lower()] for t in ("note", "clinical_note", "output", "summary") if t.lower() in m), None)
    log.info("\n-- Recommended canonical fields --")
    log.info(f"  transcript: {rec_t or 'NONE — BLOCKER'}\n  reference_note (eval only): {rec_n or 'none'}")
    log.info(f"\n-- Null / empty counts (first {null_cap:,} rows) --")
    for c, k in _null_counts(ds, cols, null_cap).items():
        log.info(f"  {c!r}: {k:,}")
    skip_stats = {"idx", "id"}
    str_cols = [
        c
        for c in cols
        if len(ds) and isinstance(ds[0].get(c), str) and c.lower() not in skip_stats
    ]
    stats_cols = list(dict.fromkeys(tm + nm + str_cols))
    log.info(f"\n-- Text length stats (sample up to {text_cap:,}) --")
    for c in stats_cols:
        lens = _text_lengths_sample(ds, c, text_cap)
        if not lens:
            continue
        st = _stats(lens)
        log.info(
            f"  {c!r}: n={int(st['n'])} min={st['min']:.0f} max={st['max']:.0f} "
            f"mean={st['mean']:.1f} p50={st['p50']:.0f} p95={st['p95']:.0f}"
        )
    log.info("\n-- First 3 records (truncated) --")
    for i in range(min(3, len(ds))):
        row = ds[i]
        log.info(f"  --- row {i} ---")
        for k in cols:
            log.info(f"    {k}: {_as_printable(row[k], max_chars)}")


def _verdict(cols: list[str], splits: dict[str, int]) -> None:
    m = _ci_map(cols)
    ok_t = any(t.lower() in m for t in TRANSCRIPT_NAMES)
    log.info("\n" + "=" * 72 + "\nVERDICT\n" + "=" * 72)
    if not splits:
        log.info("BLOCKER: No splits / empty dataset.")
        return
    if not ok_t:
        log.info("BLOCKER: No transcript column in %s", TRANSCRIPT_NAMES)
        return
    log.info(
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
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s", force=True)

    log.info("Loading %r …", args.dataset)
    kw: dict[str, Any] = {}
    if args.revision:
        kw["revision"] = args.revision
    if args.trust_remote_code:
        kw["trust_remote_code"] = True
    try:
        raw = load_dataset(args.dataset, split=args.split, **kw)
        log.debug(
            "hf_load_dataset_succeeded dataset=%r split=%r revision=%r trust_remote_code=%s",
            args.dataset,
            args.split,
            args.revision,
            args.trust_remote_code,
        )
    except Exception as e:
        log.error("BLOCKER: load_dataset failed: %s", e)
        if "trust_remote_code" in str(e).lower():
            log.error("Hint: --trust-remote-code")
        return 1

    split_lengths: dict[str, int] = {}
    all_cols: list[str] = []

    if isinstance(raw, DatasetDict):
        log.info(f"\nDataset splits: {list(raw.keys())}")
        for sn, d in raw.items():
            split_lengths[sn] = len(d)
            all_cols = d.column_names
            _report_split(sn, d, args.max_chars, args.null_sample_cap, args.text_stats_sample)
    elif isinstance(raw, Dataset):
        sn = args.split or "single"
        split_lengths[sn] = len(raw)
        all_cols = raw.column_names
        log.info("\nSingle Dataset.")
        _report_split(sn, raw, args.max_chars, args.null_sample_cap, args.text_stats_sample)
    else:
        log.info(f"\nBLOCKER: bad type {type(raw)}")
        return 1

    log.info(f"\nRow counts: {{{', '.join(f'{k!r}: {split_lengths[k]}' for k in sorted(split_lengths))}}}")
    _verdict(all_cols, split_lengths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
