#!/usr/bin/env python3
"""
Phase 1 — Local medical specialty classification on staged Parquet (no Azure, no Postgres).

Reads data/staging/manifest.json and the Parquet path in the first split; writes:
  - data/staging/specialty_predictions.jsonl
  - data/staging/specialty_prediction_summary.json

Model: anaschahid/medical-specialty-classifier (HF transformers, local inference).

See `docs/roadmap/PHASE1_MASTER_PLAN.md` §4.5 and `../README.md` (see pipeline README).

"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "anaschahid/medical-specialty-classifier"


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_device(preference: str) -> str:
    pref = (preference or "auto").strip().lower()
    if pref != "auto":
        return pref
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


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
    return v


def _text_for_row(note_val: Any, conv_val: Any) -> tuple[str, str]:
    note_s = "" if _json_val(note_val) is None else str(note_val).strip()
    conv_s = "" if _json_val(conv_val) is None else str(conv_val).strip()
    if note_s:
        return note_s, "reference_note"
    return conv_s, "conversation_text"


def _json_line(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Phase 1 — classify medical specialties for staged notes (local HF model)."
    )
    ap.add_argument("--manifest", type=Path, default=None, help="Path to manifest.json")
    ap.add_argument("--repo-root", type=Path, default=None, help="Repository root (default: infer from script)")
    ap.add_argument("--limit", type=int, default=None, help="Process at most N rows (after load)")
    ap.add_argument("--batch-size", type=int, default=16, help="Inference batch size")
    ap.add_argument(
        "--device",
        type=str,
        default="auto",
        help='Torch device: "auto" (mps/cuda/cpu), or cpu / mps / cuda',
    )
    args = ap.parse_args()

    repo = args.repo_root.resolve() if args.repo_root else _repo_root_from_script()
    manifest_path = args.manifest or (repo / "data" / "staging" / "manifest.json")
    if not manifest_path.is_file():
        print(f"BLOCKER: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    splits = manifest.get("splits") or {}
    if not splits:
        print("BLOCKER: manifest has no splits", file=sys.stderr)
        return 1
    split_name = next(iter(splits))
    rel = splits[split_name]["parquet_relative"]
    parquet_path = repo / rel
    if not parquet_path.is_file():
        print(f"BLOCKER: parquet not found: {parquet_path}", file=sys.stderr)
        return 1

    canon = manifest.get("canonical_columns") or {}
    note_col = canon.get("reference_note_column") or "note"
    conv_col = canon.get("transcript_column") or "conversation"
    idx_col = "idx"

    df = pd.read_parquet(parquet_path, columns=[idx_col, note_col, conv_col])
    for c in (idx_col, note_col, conv_col):
        if c not in df.columns:
            print(f"BLOCKER: column {c!r} missing from parquet", file=sys.stderr)
            return 1

    if args.limit is not None:
        df = df.head(args.limit).copy()

    device_str = _resolve_device(args.device)
    device = torch.device(device_str)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
    model.eval()
    model.to(device)

    id2label = model.config.id2label
    if not id2label:
        print("BLOCKER: model has no id2label", file=sys.stderr)
        return 1

    out_dir = repo / "data" / "staging"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "specialty_predictions.jsonl"
    summary_path = out_dir / "specialty_prediction_summary.json"

    n = len(df)
    batch_size = max(1, args.batch_size)
    t0 = time.perf_counter()

    label_counts: Counter[str] = Counter()
    confidences: list[float] = []
    low_confidence_count = 0
    LOW_THRESHOLD = 0.5

    first_logged = 0

    with jsonl_path.open("w", encoding="utf-8") as out_f:
        for start in tqdm(range(0, n, batch_size), desc="Specialty batches", unit="batch"):
            batch_df = df.iloc[start : start + batch_size]
            texts: list[str] = []
            sources: list[str] = []
            ids: list[str] = []
            for _, row in batch_df.iterrows():
                raw_id = _json_val(row[idx_col])
                sid = str(raw_id) if raw_id is not None else ""
                txt, src = _text_for_row(row[note_col], row[conv_col])
                ids.append(sid)
                texts.append(txt)
                sources.append(src)

            enc = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.inference_mode():
                logits = model(**enc).logits
                probs = torch.softmax(logits, dim=-1)
            top3_scores, top3_idx = torch.topk(probs, k=min(3, probs.size(-1)), dim=-1)

            for i in range(len(ids)):
                scores_i = top3_scores[i].tolist()
                idx_i = top3_idx[i].tolist()
                top_labels = []
                for sc, li in zip(scores_i, idx_i, strict=True):
                    _li = int(li)
                    lab = id2label.get(_li, str(_li))
                    top_labels.append({"label": str(lab), "score": float(sc)})

                best = top_labels[0]
                pred_label = best["label"]
                confidence = best["score"]
                label_counts[pred_label] += 1
                confidences.append(confidence)
                if confidence < LOW_THRESHOLD:
                    low_confidence_count += 1

                rec = {
                    "source_row_id": ids[i],
                    "predicted_specialty": pred_label,
                    "confidence": float(confidence),
                    "top_labels": top_labels,
                    "text_source": sources[i],
                    "model": MODEL_ID,
                }
                out_f.write(_json_line(rec) + "\n")

                if first_logged < 3:
                    print(f"[sample {first_logged + 1}] {json.dumps(rec, ensure_ascii=False)[:500]}…")
                    first_logged += 1

    runtime = time.perf_counter() - t0
    avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0

    summary = {
        "model": MODEL_ID,
        "device_used": device_str,
        "total_rows_classified": n,
        "label_distribution": dict(sorted(label_counts.items(), key=lambda x: (-x[1], x[0]))),
        "average_confidence": avg_conf,
        "low_confidence_count": low_confidence_count,
        "batch_size": batch_size,
        "runtime_seconds": round(runtime, 3),
        "output_path": str(jsonl_path.relative_to(repo)),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {jsonl_path.relative_to(repo)} ({n} lines)")
    print(f"Wrote {summary_path.relative_to(repo)}")
    print("Phase 1 specialty classification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
