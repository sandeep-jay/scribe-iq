"""Note read endpoints (T4)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.db import get_conn
import json

from app.schemas.api_patients import NoteDetail


def _coerce_json_obj(value) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}


def _coerce_json_obj_nullable(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None
    try:
        out = dict(value)
    except (TypeError, ValueError):
        return None
    return out


router = APIRouter(tags=["notes"])


@router.get("/notes/{note_id}", response_model=NoteDetail)
async def get_note(
    note_id: UUID,
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> NoteDetail:
    row = await conn.fetchrow(
        """
        SELECT id,
               patient_id,
               domain,
               external_encounter_id,
               corpus_note_id,
               specialty,
               source,
               session_date,
               created_at,
               conversation_text,
               structured_note,
               entity_payload,
               longitudinal_context,
               embedding IS NOT NULL AS embedding_present
        FROM notes
        WHERE id = $1::uuid
        """,
        note_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")

    sn = _coerce_json_obj(row["structured_note"])
    ep = _coerce_json_obj(row["entity_payload"])
    lng = _coerce_json_obj_nullable(row["longitudinal_context"])

    return NoteDetail(
        id=row["id"],
        patient_id=row["patient_id"],
        domain=row["domain"],
        external_encounter_id=row["external_encounter_id"],
        corpus_note_id=row["corpus_note_id"],
        specialty=row["specialty"],
        source=row["source"],
        session_date=row["session_date"],
        created_at=row["created_at"],
        conversation_text=row["conversation_text"],
        structured_note=sn,
        entity_payload=ep,
        longitudinal_context=lng,
        embedding_present=bool(row["embedding_present"]),
    )
