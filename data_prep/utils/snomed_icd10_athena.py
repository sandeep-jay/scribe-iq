"""Build SNOMED CT concept_code → ICD-10-CM code from OHDSI Athena CSV export.

Expects ``CONCEPT.csv`` and ``CONCEPT_RELATIONSHIP.csv`` (tab-separated). Uses rows
where ``relationship_id`` is ``Mapped from``, ``concept_id_1`` is **SNOMED** and
``concept_id_2`` is **ICD10CM** (standard → billing / non-standard in OMOP).

Vocabulary files are license-bound (SNOMED, etc.); do not commit CSV extracts.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path


def discover_athena_vocab_dir(repo_root: Path) -> Path | None:
    env = os.environ.get("ATHENA_VOCAB_DIR", "").strip()
    if env:
        p = Path(env).expanduser()
        if (p / "CONCEPT.csv").is_file() and (p / "CONCEPT_RELATIONSHIP.csv").is_file():
            return p
    default = repo_root / "data/snomed_icd10/vocabulary"
    if (default / "CONCEPT.csv").is_file() and (default / "CONCEPT_RELATIONSHIP.csv").is_file():
        return default
    return None


def _icd10cm_preference_key(code: str) -> tuple[int, str]:
    """Prefer clinical diagnosis chapters over Zxx (factors influencing health status)."""
    c = (code or "").strip().upper()
    z_penalty = 1 if c.startswith("Z") else 0
    return (z_penalty, c)


def load_athena_snomed_icd10cm(vocab_dir: Path) -> dict[str, str]:
    """Return SCTID string → ICD-10-CM code string (OMOP ``concept_code`` form).

    When several ICD10CM targets exist for one SNOMED, prefer **non-Z** codes, then
    lexicographically smallest for stable, deterministic output.
    """
    concept_path = vocab_dir / "CONCEPT.csv"
    rel_path = vocab_dir / "CONCEPT_RELATIONSHIP.csv"

    id_vocab: dict[int, tuple[str, str]] = {}
    with concept_path.open(encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) < 10:
                continue
            if row[3] not in ("SNOMED", "ICD10CM") or row[9]:
                continue
            try:
                cid = int(row[0])
            except ValueError:
                continue
            id_vocab[cid] = (row[3], row[6])

    out: dict[str, str] = {}
    with rel_path.open(encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) < 6:
                continue
            if row[2] != "Mapped from" or row[5]:
                continue
            try:
                c1, c2 = int(row[0]), int(row[1])
            except ValueError:
                continue
            t1 = id_vocab.get(c1)
            t2 = id_vocab.get(c2)
            if not t1 or not t2:
                continue
            v1, code1 = t1
            v2, code2 = t2
            if v1 != "SNOMED" or v2 != "ICD10CM":
                continue
            prev = out.get(code1)
            if prev is None or _icd10cm_preference_key(code2) < _icd10cm_preference_key(prev):
                out[code1] = code2
    return out
