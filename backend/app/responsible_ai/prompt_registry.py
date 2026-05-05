"""Logical prompt versions for governance / audit."""

from __future__ import annotations

from typing import Any, TypedDict


class PromptMeta(TypedDict, total=False):
    use_case: str
    requires_citations: bool
    requires_sources: bool
    requires_human_review: bool
    clinical_disclaimer: bool


CHAT_RAG_V1 = "chat_rag_v1"
NOTE_GENERATION_V1 = "note_generation_v1"
MEETING_PREP_V1 = "meeting_prep_v1"

PROMPTS: dict[str, PromptMeta] = {
    CHAT_RAG_V1: {
        "use_case": "RAG chat",
        "requires_citations": True,
        "clinical_disclaimer": True,
    },
    MEETING_PREP_V1: {
        "use_case": "Pre-meeting summary",
        "requires_sources": True,
    },
    NOTE_GENERATION_V1: {
        "use_case": "Structured note generation",
        "requires_human_review": True,
    },
}


def meta_for_prompt_version(pv: str | None) -> dict[str, Any]:
    if not pv:
        return {}
    if pv.startswith("scribe-meeting-prep") or pv.startswith("meeting_prep"):
        return dict(PROMPTS[MEETING_PREP_V1])
    if "note_generation" in pv or pv == NOTE_GENERATION_V1:
        return dict(PROMPTS[NOTE_GENERATION_V1])
    if pv == CHAT_RAG_V1:
        return dict(PROMPTS[CHAT_RAG_V1])
    return dict(PROMPTS.get(pv, PROMPTS[CHAT_RAG_V1]))
