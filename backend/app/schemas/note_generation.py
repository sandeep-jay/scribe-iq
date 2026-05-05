"""Request/response + LLM-validated structured note for POST /notes/generate."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StructuredGeneratedNote(BaseModel):
    chief_complaint: str
    history: str
    examination: str
    assessment: str
    plan: str
    follow_up: str
    summary: str = Field(description="Brief clinical synopsis (no invented facts)")
    sentiment: str = Field(default="neutral")
    topics: list[str] = Field(default_factory=list)
    full_note: str

    @field_validator("topics", mode="before")
    @classmethod
    def _coerce_topics(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [str(value)]
        out: list[str] = []
        for x in value[:12]:
            s = str(x).strip()
            if s:
                out.append(s)
        return out[:8]

    def as_jsonb_obj(self) -> dict[str, Any]:
        data = self.model_dump()
        return data


class NoteGenerationAudit(BaseModel):
    interaction_id: UUID
    prompt_version: str
    requires_human_review: bool = True
    safety_status: str


class GenerateNoteRequest(BaseModel):
    patient_id: str = Field(description="Patient UUID string or external_id")
    transcript: str = Field(min_length=1, max_length=200_000)
    specialty: str | None = Field(default=None, max_length=256)
    session_date: date | None = None
    external_encounter_id: str | None = Field(
        default=None,
        description="Encounter key; omit to mint generated-<uuid>. Required when replace_existing is true.",
        max_length=512,
    )
    replace_existing: bool = Field(
        default=False,
        description="Regenerate/update an encounter row keyed by external_encounter_id for this patient.",
    )


class GenerateNoteResponse(BaseModel):
    note_id: UUID
    external_encounter_id: str
    structured_note: dict[str, Any]
    embedding_written: bool
    replaced_existing: bool
    audit: NoteGenerationAudit | None = None
