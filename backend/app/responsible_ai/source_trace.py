"""Normalize retrieval / citation payloads for audit JSON columns."""

from __future__ import annotations

from typing import Any


def trace_from_chat_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    note_ids = [str(r.get("note_id")) for r in rows if r.get("note_id") is not None]
    scores = []
    for r in rows:
        if r.get("cosine_sim") is not None:
            try:
                scores.append(float(r["cosine_sim"]))
            except (TypeError, ValueError):
                continue
    return {
        "retrieved_note_ids": note_ids,
        "scores": scores,
        "citation_count": len(note_ids),
        "source_fingerprint": None,
    }


def trace_from_meeting_prep_visits(visits: list[dict[str, Any]], *, fingerprint: str) -> dict[str, Any]:
    ids: list[str] = []
    for v in visits:
        nid = v.get("note_id")
        if nid is not None:
            ids.append(str(nid))
    return {
        "retrieved_note_ids": ids,
        "scores": [],
        "citation_count": len(ids),
        "source_fingerprint": fingerprint,
    }
