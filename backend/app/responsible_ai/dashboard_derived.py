"""Derived fields for Responsible AI admin dashboard (risk tier, counts, labels)."""

from __future__ import annotations

import json
from typing import Any


# Ordered taxonomy for breakdown UI (includes every code emitted by safety_checks today).
SAFETY_FLAG_TAXONOMY: list[tuple[str, str]] = [
    ("no_citations", "No citations"),
    ("low_citation_coverage", "Low citation coverage"),
    ("no_sources_in_bundle", "No sources in bundle"),
    ("low_content_output", "Low content output"),
    ("excessive_uncertainty", "Excessive uncertainty"),
]


def _parse_jsonb(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, dict | list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return None
    return None


def count_retrieved_sources(retrieved_sources_json: Any) -> int:
    obj = _parse_jsonb(retrieved_sources_json)
    if isinstance(obj, dict):
        ids = obj.get("retrieved_note_ids")
        if isinstance(ids, list):
            return len(ids)
        cc = obj.get("citation_count")
        if isinstance(cc, int) and cc >= 0:
            return cc
    return 0


def count_citations(citations_json: Any) -> int:
    obj = _parse_jsonb(citations_json)
    if isinstance(obj, list):
        return len(obj)
    return 0


def parse_safety_flags(safety_flags_json: Any) -> list[dict[str, Any]]:
    obj = _parse_jsonb(safety_flags_json)
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    return []


def governance_bool(governance_json: Any, key: str) -> bool:
    g = _parse_jsonb(governance_json)
    if not isinstance(g, dict):
        return False
    v = g.get(key)
    return bool(v) if v is not None else False


def derive_run_mode(
    *,
    interaction_type: str,
    governance_json: Any,
) -> str:
    """Human-readable generation mode for the interaction row."""
    if interaction_type == "meeting_prep":
        return "cached" if governance_bool(governance_json, "cached") else "generated"
    return "generated"


def derive_latency_display(
    *,
    interaction_type: str,
    governance_json: Any,
    latency_ms: int | None,
) -> dict[str, Any]:
    """Avoid misleading sub-millisecond averages for cache-hit audit rows."""
    cached = interaction_type == "meeting_prep" and governance_bool(governance_json, "cached")
    if latency_ms is None:
        return {
            "latency_ms": None,
            "kind": "unknown",
            "label": "—",
            "cached": cached,
        }
    if cached and latency_ms <= 5:
        return {
            "latency_ms": latency_ms,
            "kind": "cached",
            "label": "Cached",
            "cached": True,
        }
    return {
        "latency_ms": latency_ms,
        "kind": "fresh",
        "label": f"{int(latency_ms)} ms",
        "cached": False,
    }


def derive_risk_tier(
    *,
    interaction_type: str,
    status: str | None,
    citation_count: int,
    source_count: int,
    safety_flags: list[dict[str, Any]],
    governance_json: Any,
) -> str:
    """
    Heuristic risk tier for enterprise dashboards — not clinical safety classification.
    """
    st = (status or "").lower()
    if st in ("failed", "blocked"):
        return "high"
    codes = {str(f.get("code") or "") for f in safety_flags}
    if "no_citations" in codes or "no_sources_in_bundle" in codes:
        if interaction_type == "chat" and citation_count <= 0:
            return "high" if source_count <= 0 else "medium"
        if interaction_type == "meeting_prep" and source_count <= 0:
            return "high"
    if interaction_type == "chat" and citation_count <= 0:
        return "medium"
    if interaction_type == "note_generation" and governance_bool(governance_json, "requires_human_review"):
        return "medium"
    if any(str(f.get("severity") or "") == "high" for f in safety_flags if not f.get("pass", True)):
        return "high"
    if any(not f.get("pass", True) for f in safety_flags):
        return "medium"
    if st == "degraded":
        return "medium"
    return "low"


def merge_safety_counts(existing: dict[str, int]) -> dict[str, int]:
    out = {code: int(existing.get(code) or 0) for code, _ in SAFETY_FLAG_TAXONOMY}
    for k, v in existing.items():
        if k in out:
            out[k] = int(v)
    return out
