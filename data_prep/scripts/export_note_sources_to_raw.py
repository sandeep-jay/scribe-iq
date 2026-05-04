"""
export_note_sources_to_raw.py

Download MedSynth + MTSamples from HuggingFace and write immutable JSONL snapshots
under data/raw/ for reproducibility.

Optional: MEDSYNTH_REVISION, MTSAMPLES_REVISION (git refs for the dataset repos).

Run from repo:  python data_prep/scripts/export_note_sources_to_raw.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_DP_ROOT = Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))

from datasets import load_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _export_jsonl(dataset_id: str, split: str, out_dir: Path, revision: str | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{split}.jsonl"
    kw = {}
    if revision:
        kw["revision"] = revision
    ds = load_dataset(dataset_id, split=split, **kw)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    manifest = {
        "dataset_id": dataset_id,
        "split": split,
        "revision": revision or "(default branch / snapshot at export time)",
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": n,
        "artifact": str(out_path.relative_to(REPO_ROOT)),
        "sha256": _sha256(out_path),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"✓ {dataset_id}  rows={n}  → {out_path}")


def main() -> None:
    med_rev = os.environ.get("MEDSYNTH_REVISION")
    mts_rev = os.environ.get("MTSAMPLES_REVISION")

    _export_jsonl(
        "Ahmad0067/MedSynth",
        "train",
        REPO_ROOT / "data/raw/hf_medsynth",
        med_rev,
    )
    _export_jsonl(
        "harishnair04/mtsamples",
        "train",
        REPO_ROOT / "data/raw/hf_mtsamples",
        mts_rev,
    )
    print("\nSnapshots ready under data/raw/hf_*/")


if __name__ == "__main__":
    main()
