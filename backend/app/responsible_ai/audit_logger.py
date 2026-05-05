"""Insert rows into ai_interactions (append-only audit trail)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg


async def insert_ai_interaction(
    conn: asyncpg.Connection,
    *,
    request_id: str,
    interaction_type: str,
    patient_id: str | None,
    note_id: str | None,
    model_provider: str | None,
    model_name: str | None,
    prompt_version: str | None,
    system_prompt_hash: str | None,
    input_hash: str | None,
    output_hash: str | None,
    input_redacted_preview: str | None,
    output_redacted_preview: str | None,
    retrieved_sources_json: Any,
    citations_json: Any,
    safety_flags_json: Any,
    governance_json: Any,
    latency_ms: int | None,
    input_tokens: int | None,
    output_tokens: int | None,
    status: str,
    error_message: str | None = None,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO ai_interactions (
          request_id, interaction_type, patient_id, note_id,
          model_provider, model_name, prompt_version, system_prompt_hash,
          input_hash, output_hash, input_redacted_preview, output_redacted_preview,
          retrieved_sources_json, citations_json, safety_flags_json, governance_json,
          latency_ms, input_tokens, output_tokens, status, error_message
        ) VALUES (
          $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,
          $13::jsonb,$14::jsonb,$15::jsonb,$16::jsonb,
          $17,$18,$19,$20,$21
        )
        RETURNING id
        """,
        request_id,
        interaction_type,
        patient_id,
        note_id,
        model_provider,
        model_name,
        prompt_version,
        system_prompt_hash,
        input_hash,
        output_hash,
        input_redacted_preview,
        output_redacted_preview,
        retrieved_sources_json,
        citations_json,
        safety_flags_json,
        governance_json,
        latency_ms,
        input_tokens,
        output_tokens,
        status,
        error_message,
    )
    assert row is not None
    return row["id"]
