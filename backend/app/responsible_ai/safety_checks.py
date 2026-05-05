"""Lightweight deterministic safety / quality signals for demos."""

from __future__ import annotations

from typing import Any


def _worst(severities: list[str]) -> str:
    if any(s == "high" for s in severities):
        return "warning"
    if any(s == "medium" for s in severities):
        return "warning"
    return "pass"


def aggregate_safety_status(flags: list[dict[str, Any]]) -> str:
    sev = [str(f.get("severity") or "low") for f in flags if not f.get("pass", True)]
    return _worst(sev) if sev else "pass"


def evaluate_chat(
    *,
    answer: str,
    citations_count: int,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if citations_count <= 0:
        flags.append(
            {
                "code": "no_citations",
                "severity": "high",
                "pass": False,
                "message": "No citation chunks were attached to the response.",
            }
        )
    elif citations_count < 2:
        flags.append(
            {
                "code": "low_citation_coverage",
                "severity": "medium",
                "pass": False,
                "message": "Few retrieval neighbors were used.",
            }
        )
    if len(answer.strip()) < 40:
        flags.append(
            {
                "code": "low_content_output",
                "severity": "medium",
                "pass": False,
                "message": "Model output is very short.",
            }
        )
    hedge = ("cannot tell", "not enough", "insufficient evidence", "unclear", "i don't know")
    al = answer.casefold()
    if sum(1 for h in hedge if h in al) >= 3:
        flags.append(
            {
                "code": "excessive_uncertainty",
                "severity": "low",
                "pass": False,
                "message": "Answer contains multiple uncertainty phrases.",
            }
        )
    return flags


def evaluate_note_json_preview(note_json_text: str) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if len(note_json_text.strip()) < 80:
        flags.append(
            {
                "code": "low_content_output",
                "severity": "medium",
                "pass": False,
                "message": "Structured note payload is very small.",
            }
        )
    return flags


def evaluate_meeting_prep(*, summary: str, visit_note_ids: list[str]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if not visit_note_ids:
        flags.append(
            {
                "code": "no_sources_in_bundle",
                "severity": "medium",
                "pass": False,
                "message": "No encounter rows were included in the prep bundle.",
            }
        )
    if len(summary.strip()) < 60:
        flags.append(
            {
                "code": "low_content_output",
                "severity": "medium",
                "pass": False,
                "message": "Meeting prep summary is very short.",
            }
        )
    return flags
