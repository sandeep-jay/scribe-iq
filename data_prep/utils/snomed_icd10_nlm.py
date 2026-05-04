"""Merged SNOMED CT → ICD-10-CM map: Athena (OHDSI) CSV and/or NLM ExtendedMap.

**Athena (default path:** ``data/snomed_icd10/vocabulary`` or ``ATHENA_VOCAB_DIR``): builds
from ``CONCEPT.csv`` + ``CONCEPT_RELATIONSHIP.csv`` (``Mapped from`` SNOMED → ICD10CM).

**NLM:** RF2 ExtendedMap (refset **6011000124106**), file
``der2_iisssccRefset_ExtendedMapSnapshot_US1000124_*.txt``.
https://www.nlm.nih.gov/research/umls/mapping_projects/snomedct_to_icd10cm.html

Merge order: built-in fallback, then Athena, then NLM (authoritative when present).

Do not commit large vocabulary extracts; respect SNOMED / Athena license terms.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from utils.mappings import SNOMED_TO_ICD10_FALLBACK

from utils.snomed_icd10_athena import discover_athena_vocab_dir, load_athena_snomed_icd10cm

# NLM: ICD-10-CM complex map reference set (foundation metadata concept)
DEFAULT_ICD10CM_MAP_REFSET_ID = "6011000124106"

# RF2 ExtendedMap: id, effectiveTime, active, moduleId, refsetId, referencedComponentId,
# mapGroup, mapPriority, mapRule, mapAdvice, mapTarget, ...
_IDX_ACTIVE = 2
_IDX_REFSET = 4
_IDX_COMPONENT = 5
_IDX_GROUP = 6
_IDX_PRIORITY = 7
_IDX_TARGET = 10


def normalize_snomed_concept_id(code) -> str | None:
    """Match Synthea / pandas codes to plain SCTID digits (no version suffix)."""
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return None
    try:
        return str(int(float(code)))
    except (TypeError, ValueError):
        s = str(code).strip()
        if not s:
            return None
        return s.split(".")[0]


def load_nlm_extended_map_snapshot(path: Path, *, refset_id: str | None = None) -> dict[str, str]:
    """Parse one NLM ExtendedMap snapshot; pick lowest (mapGroup, mapPriority) per SNOMED concept."""
    rid = (refset_id or os.environ.get("SNOMED_ICD10_MAP_REFSET_ID") or "").strip()
    if not rid:
        rid = DEFAULT_ICD10CM_MAP_REFSET_ID

    best: dict[str, tuple[tuple[int, int], str]] = {}
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) <= _IDX_TARGET:
                continue
            if parts[_IDX_ACTIVE] != "1":
                continue
            if parts[_IDX_REFSET] != rid:
                continue
            snomed = parts[_IDX_COMPONENT].strip()
            if not snomed:
                continue
            try:
                grp = int(parts[_IDX_GROUP])
                pri = int(parts[_IDX_PRIORITY])
            except ValueError:
                continue
            target = parts[_IDX_TARGET].strip()
            if not target:
                continue
            key_rank = (grp, pri)
            prev = best.get(snomed)
            if prev is None or key_rank < prev[0]:
                best[snomed] = (key_rank, target)
    return {s: t for s, (_, t) in best.items()}


def discover_extended_map_file(repo_root: Path) -> Path | None:
    env = os.environ.get("SNOMED_ICD10_EXTENDED_MAP_FILE", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    raw = repo_root / "data/raw/snomed_icd10cm"
    if raw.is_dir():
        matches = sorted(raw.rglob("der2_iisssccRefset_ExtendedMapSnapshot*.txt"))
        if matches:
            return matches[-1]
    return None


@lru_cache(maxsize=4)
def _merged_snomed_icd10_cached(repo_root_str: str) -> dict[str, str]:
    repo_root = Path(repo_root_str)
    merged: dict[str, str] = dict(SNOMED_TO_ICD10_FALLBACK)

    athena_dir = discover_athena_vocab_dir(repo_root)
    if athena_dir is not None:
        athena = load_athena_snomed_icd10cm(athena_dir)
        merged.update(athena)
        print(
            f"SNOMED→ICD-10-CM: Athena vocabulary {athena_dir} → {len(athena):,} SNOMED keys"
        )

    nlm_path = discover_extended_map_file(repo_root)
    if nlm_path is not None:
        nlm = load_nlm_extended_map_snapshot(nlm_path)
        merged.update(nlm)
        print(
            f"SNOMED→ICD-10-CM: NLM {nlm_path.name} → {len(nlm):,} rows "
            f"(refset {DEFAULT_ICD10CM_MAP_REFSET_ID})"
        )

    if athena_dir is None and nlm_path is None:
        print(
            "SNOMED→ICD-10-CM: built-in fallback only (~50 codes). Add Athena CSVs under "
            "data/snomed_icd10/vocabulary or set ATHENA_VOCAB_DIR, and/or add NLM ExtendedMap "
            "(SNOMED_ICD10_EXTENDED_MAP_FILE / data/raw/snomed_icd10cm/)."
        )

    return merged


def get_snomed_icd10_map(repo_root: Path) -> dict[str, str]:
    """Merged ICD-10-CM targets: fallback, Athena (if present), NLM ExtendedMap (if present)."""
    return _merged_snomed_icd10_cached(str(repo_root.resolve()))


def lookup_icd10_cm(map: dict[str, str], raw_snomed) -> str:
    k = normalize_snomed_concept_id(raw_snomed)
    if not k:
        return ""
    return map.get(k, "") or ""
