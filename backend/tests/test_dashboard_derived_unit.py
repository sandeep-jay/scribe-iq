from __future__ import annotations

from app.responsible_ai.dashboard_derived import count_citations, count_retrieved_sources, derive_latency_display, derive_risk_tier, derive_run_mode, merge_safety_counts, parse_safety_flags


def test_count_retrieved_sources_from_payload() -> None:
    assert count_retrieved_sources({"retrieved_note_ids": ["a", "b", "c"]}) == 3


def test_count_citations_from_list() -> None:
    assert count_citations([{"note_id": "1"}, {"note_id": "2"}]) == 2


def test_parse_safety_flags_handles_json_string() -> None:
    parsed = parse_safety_flags('[{"code":"no_citations","pass":false}]')
    assert parsed[0]["code"] == "no_citations"


def test_derive_run_mode_cached() -> None:
    assert derive_run_mode(interaction_type="meeting_prep", governance_json={"cached": True}) == "cached"


def test_derive_latency_display_cached_label() -> None:
    out = derive_latency_display(interaction_type="meeting_prep", governance_json={"cached": True}, latency_ms=3)
    assert out["label"] == "Cached"


def test_derive_risk_tier_high_for_failed_or_no_sources() -> None:
    assert derive_risk_tier(
        interaction_type="chat",
        status="failed",
        citation_count=0,
        source_count=0,
        safety_flags=[],
        governance_json={},
    ) == "high"


def test_merge_safety_counts_keeps_taxonomy_keys() -> None:
    merged = merge_safety_counts({"no_citations": 2})
    assert merged["no_citations"] == 2
    assert "low_content_output" in merged
