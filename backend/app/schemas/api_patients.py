from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    name: str
    metadata: dict[str, Any]
    note_count: int
    last_session_date: date | None
    has_longitudinal: bool = False
    last_specialty: str | None = None


class NotePreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_encounter_id: str
    corpus_note_id: str | None
    session_date: date | None
    specialty: str | None
    summary: str | None
    has_dialogue: bool


class PatientDetail(BaseModel):
    id: UUID
    external_id: str
    name: str
    metadata: dict[str, Any]
    note_count: int
    latest_longitudinal: dict[str, Any] | None
    longitudinal_medication_hints: list[str]
    notes: list[NotePreview]


class PaginatedPatients(BaseModel):
    patients: list[PatientListItem]
    total: int
    limit: int
    offset: int


class NoteDetail(BaseModel):
    id: UUID
    patient_id: UUID
    domain: str
    external_encounter_id: str
    corpus_note_id: str | None
    specialty: str | None
    source: str | None
    session_date: date | None
    created_at: datetime
    conversation_text: str
    structured_note: dict[str, Any]
    entity_payload: dict[str, Any]
    longitudinal_context: dict[str, Any] | None
    embedding_present: bool


class CorpusPatientStats(BaseModel):
    domain: str
    total_patients: int
    total_notes: int


class MeetingPrepResponse(BaseModel):
    patient_id: UUID
    summary: str
    generated_at: datetime
    cached: bool
    prompt_version: str
    model: str
    degraded: bool = False

