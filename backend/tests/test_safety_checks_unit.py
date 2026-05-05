from __future__ import annotations

from app.responsible_ai.safety_checks import aggregate_safety_status, evaluate_chat, evaluate_meeting_prep, evaluate_note_json_preview


def test_evaluate_chat_flags_citation_and_short_answer() -> None:
    flags = evaluate_chat(answer="short", citations_count=0)
    codes = {f["code"] for f in flags}
    assert "no_citations" in codes
    assert "low_content_output" in codes


def test_evaluate_chat_uncertainty_phrase_detection() -> None:
    answer = "I cannot tell. This is unclear. I don't know because there is not enough evidence."
    flags = evaluate_chat(answer=answer, citations_count=2)
    assert any(f["code"] == "excessive_uncertainty" for f in flags)


def test_note_json_preview_small_payload_flagged() -> None:
    flags = evaluate_note_json_preview("{}")
    assert any(f["code"] == "low_content_output" for f in flags)


def test_meeting_prep_flags_when_empty_sources_and_short_summary() -> None:
    flags = evaluate_meeting_prep(summary="too short", visit_note_ids=[])
    codes = {f["code"] for f in flags}
    assert "no_sources_in_bundle" in codes
    assert "low_content_output" in codes


def test_aggregate_status_prefers_warning() -> None:
    status = aggregate_safety_status([{"pass": False, "severity": "low"}, {"pass": False, "severity": "medium"}])
    assert status == "warning"
