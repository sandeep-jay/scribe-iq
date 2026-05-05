"""Schemas for POST /chat (vector RAG + Groq)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCitation(BaseModel):
    note_id: UUID
    similarity: float
    excerpt: str
    summary: str | None = None
    external_encounter_id: str | None = None


class ChatAuditBlock(BaseModel):
    interaction_id: UUID
    model: str | None = None
    prompt_version: str
    source_count: int
    safety_status: str
    latency_ms: int


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=16384)
    patient_id: str | None = Field(
        default=None,
        description="Restrict retrieval to notes for this UUID or external patient id.",
    )
    domain: str = Field(default="clinical")
    top_k: Annotated[int, Field(ge=1, le=24, description="Neighbor count for retrieval.")] = 8
    conversation: list[ChatTurn] = Field(
        default_factory=list,
        description="Optional prior turns (user/assistant) for continuity.",
    )


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]
    audit: ChatAuditBlock | None = None
