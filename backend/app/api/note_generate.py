"""Guarded transcript -> structured_note persistence (T6).

Writes are **opt-in** via ``NOTE_GENERATION_ENABLED``. The handler validates structured JSON from Groq,
persists to ``notes``, optionally backfills embeddings, and writes an ``ai_interactions`` audit row.

Logging: ``INFO`` for milestones; ``DEBUG`` for branch selection and dimensions (no transcript text).
"""

from __future__ import annotations

import json

import structlog
import uuid
from typing import Annotated

import asyncpg
import asyncpg.exceptions
from fastapi import APIRouter, Depends, HTTPException, Request

from app.request_id import get_request_id
from app.api.patients import resolve_patient_id
from app.config import get_settings
from app.db import get_conn
from app.embeddings import compose_note_embed_input, embed_and_vector_literal
from app.llm import GroqCompletionResult, groq_chat_json_completion
from app.responsible_ai.audit_logger import insert_ai_interaction
from app.responsible_ai.hashes import sha256_hex
from app.responsible_ai.prompt_registry import NOTE_GENERATION_V1
from app.responsible_ai.redaction import redact_preview
from app.responsible_ai.safety_checks import aggregate_safety_status, evaluate_note_json_preview
from app.schemas.note_generation import (
    GenerateNoteRequest,
    GenerateNoteResponse,
    NoteGenerationAudit,
    StructuredGeneratedNote,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["notes"])

NOTE_GEN_SYSTEM_PROMPT = (
    "Return one JSON object only (no prose). Fields (clinical strings unless noted):\n"
    "chief_complaint, history, examination, assessment, plan, follow_up,\n"
    "summary (2–5 succinct sentences grounded in the transcript),\n"
    'sentiment: one of "neutral","positive concern","negative concern",\n'
    "topics: JSON array (max 8) of short clinically relevant phrases,\n"
    "full_note: narrative consolidating the SOAP fields.\n"
    "Everything must derive from transcript content; unsupported sections "
    'should read "Not discussed". Do not invent patient identifiers.'
)


async def _audit_note_row(
    conn: asyncpg.Connection,
    *,
    request_id: str,
    patient_uuid: uuid.UUID,
    note_id: uuid.UUID,
    groq_res: GroqCompletionResult,
    structured_blob: dict[str, object],
    transcript: str,
    settings,
) -> NoteGenerationAudit:
    out_blob = json.dumps(structured_blob, default=str)
    flags = evaluate_note_json_preview(out_blob)
    safety_status = aggregate_safety_status(flags)
    summary_preview = str(structured_blob.get("summary") or "")[:4000]
    interaction_id = await insert_ai_interaction(
        conn,
        request_id=request_id,
        interaction_type="note_generation",
        patient_id=str(patient_uuid),
        note_id=str(note_id),
        model_provider=settings.llm_provider,
        model_name=groq_res.model,
        prompt_version=NOTE_GENERATION_V1,
        system_prompt_hash=sha256_hex(NOTE_GEN_SYSTEM_PROMPT),
        input_hash=sha256_hex(transcript),
        output_hash=sha256_hex(out_blob),
        input_redacted_preview=redact_preview(transcript),
        output_redacted_preview=redact_preview(summary_preview or out_blob[:2000]),
        retrieved_sources_json=None,
        citations_json=None,
        safety_flags_json=flags,
        governance_json={"requires_human_review": True, "prompt_version": NOTE_GENERATION_V1},
        latency_ms=groq_res.latency_ms,
        input_tokens=groq_res.prompt_tokens,
        output_tokens=groq_res.completion_tokens,
        status="success",
        error_message=None,
    )
    return NoteGenerationAudit(
        interaction_id=interaction_id,
        prompt_version=NOTE_GENERATION_V1,
        requires_human_review=True,
        safety_status=safety_status,
    )


@router.post("/notes/generate", response_model=GenerateNoteResponse)
async def generate_note(
    request: Request,
    body: GenerateNoteRequest,
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> GenerateNoteResponse:
    settings = get_settings()
    req_id = get_request_id(request)

    logger.info(
        "note_generate_started",
        request_id=req_id,
        replace_existing=bool(body.replace_existing),
        has_external_encounter_id=bool((body.external_encounter_id or "").strip()),
        transcript_chars=len((body.transcript or "").strip()),
    )

    if not settings.note_generation_enabled:
        logger.warning("note_generate_disabled", request_id=req_id)
        raise HTTPException(
            status_code=403,
            detail="Note generation disabled. Set NOTE_GENERATION_ENABLED=true in backend/.env for trusted demos.",
        )

    patient_uuid = await resolve_patient_id(conn, body.patient_id)
    transcript = body.transcript.strip()
    logger.debug("note_generate_patient_resolved", request_id=req_id, transcript_chars=len(transcript))

    msgs = [
        {"role": "system", "content": NOTE_GEN_SYSTEM_PROMPT},
        {"role": "user", "content": f"Transcript:\n{transcript}"},
    ]

    logger.debug(
        "note_generate_llm_call_started",
        request_id=req_id,
        provider=settings.llm_provider,
        temperature=0.15,
    )
    try:
        groq_res = await groq_chat_json_completion(msgs, temperature=0.15)
        raw_json = groq_res.text
        payload = json.loads(raw_json)
        structured = StructuredGeneratedNote.model_validate(payload)
    except (json.JSONDecodeError, RuntimeError, ValueError) as e:
        logger.warning("note_generation_validation_failed", request_id=req_id, error=str(e))
        raise HTTPException(status_code=502, detail=f"LLM structured output rejected: {e}") from e

    structured_blob = structured.as_jsonb_obj()
    logger.info(
        "note_generate_structured_ok",
        request_id=req_id,
        model=groq_res.model,
        latency_ms=groq_res.latency_ms,
        prompt_tokens=groq_res.prompt_tokens,
        completion_tokens=groq_res.completion_tokens,
    )
    embedding_written = False
    encounter_id = (
        body.external_encounter_id.strip()
        if (body.external_encounter_id or "").strip()
        else None
    )

    if body.replace_existing:
        logger.debug("note_generate_replace_path", request_id=req_id, encounter_key_set=bool(encounter_id))
        if not encounter_id:
            raise HTTPException(
                status_code=400,
                detail="replace_existing requires external_encounter_id.",
            )

        prow = await conn.fetchrow(
            """
            UPDATE notes SET
              conversation_text = $1,
              structured_note = $2::jsonb,
              entity_payload = '{}'::jsonb,
              specialty = COALESCE($3, specialty),
              session_date = COALESCE($4, session_date),
              source = 'llm_regenerated',
              embedding = NULL
            WHERE patient_id = $5::uuid AND external_encounter_id = $6
            RETURNING id, external_encounter_id
            """,
            transcript,
            json.dumps(structured_blob),
            body.specialty,
            body.session_date,
            patient_uuid,
            encounter_id,
        )
        if not prow:
            logger.warning("note_generate_replace_missing_row", request_id=req_id)
            raise HTTPException(status_code=404, detail="Note not found for replace_existing.")

        logger.info("note_generate_replace_row_found", request_id=req_id, note_id=str(prow["id"]))

        note_id = prow["id"]
        final_encounter = prow["external_encounter_id"]

        lit = await embed_and_vector_literal(
            compose_note_embed_input(structured_blob, transcript)
        )
        if lit is not None:
            await conn.execute(
                "UPDATE notes SET embedding = $1::vector WHERE id = $2::uuid",
                lit,
                note_id,
            )
            embedding_written = True
            logger.debug("note_generate_embedding_replace_written", request_id=req_id, note_id=str(note_id))
        else:
            logger.debug("note_generate_embedding_replace_skipped", request_id=req_id, note_id=str(note_id))

        audit = await _audit_note_row(
            conn,
            request_id=req_id,
            patient_uuid=patient_uuid,
            note_id=note_id,
            groq_res=groq_res,
            structured_blob=structured_blob,
            transcript=transcript,
            settings=settings,
        )

        logger.info(
            "note_generate_replace_complete",
            request_id=req_id,
            note_id=str(note_id),
            embedding_written=embedding_written,
            interaction_id=audit.interaction_id,
        )
        return GenerateNoteResponse(
            note_id=note_id,
            external_encounter_id=str(final_encounter),
            structured_note=structured_blob,
            embedding_written=embedding_written,
            replaced_existing=True,
            audit=audit,
        )

    logger.debug("note_generate_insert_path", request_id=req_id, encounter_key_set=bool(encounter_id))

    new_encounter_id = encounter_id or f"generated-{uuid.uuid4()}"

    try:
        ins = await conn.fetchrow(
            """
            INSERT INTO notes (
              patient_id, domain, external_encounter_id, corpus_note_id,
              conversation_text, structured_note, entity_payload, longitudinal_context,
              specialty, source, session_date
            )
            VALUES (
              $1::uuid, 'clinical', $2::text, NULL,
              $3::text, $4::jsonb, '{}'::jsonb, NULL,
              $5::text, 'llm', $6::date
            )
            RETURNING id, external_encounter_id
            """,
            patient_uuid,
            new_encounter_id,
            transcript,
            json.dumps(structured_blob),
            body.specialty,
            body.session_date,
        )
    except asyncpg.exceptions.UniqueViolationError:
        logger.warning("note_generate_duplicate_encounter_id", request_id=req_id, encounter_id=new_encounter_id)
        raise HTTPException(
            status_code=409,
            detail=(
                "external_encounter_id already exists. Retry with replace_existing=true "
                "to overwrite for this encounter key."
            ),
        ) from None

    assert ins is not None
    note_id = ins["id"]
    final_encounter = ins["external_encounter_id"]
    logger.info("note_generate_insert_ok", request_id=req_id, note_id=str(note_id), external_encounter_id=str(final_encounter))

    lit = await embed_and_vector_literal(
        compose_note_embed_input(structured_blob, transcript)
    )
    if lit is not None:
        await conn.execute(
            "UPDATE notes SET embedding = $1::vector WHERE id = $2::uuid",
            lit,
            note_id,
        )
        embedding_written = True
        logger.debug("note_generate_embedding_insert_written", request_id=req_id, note_id=str(note_id))
    else:
        logger.debug("note_generate_embedding_insert_skipped", request_id=req_id, note_id=str(note_id))

    audit = await _audit_note_row(
        conn,
        request_id=req_id,
        patient_uuid=patient_uuid,
        note_id=note_id,
        groq_res=groq_res,
        structured_blob=structured_blob,
        transcript=transcript,
        settings=settings,
    )

    logger.info(
        "note_generate_insert_complete",
        request_id=req_id,
        note_id=str(note_id),
        embedding_written=embedding_written,
        interaction_id=audit.interaction_id,
    )

    return GenerateNoteResponse(
        note_id=note_id,
        external_encounter_id=str(final_encounter),
        structured_note=structured_blob,
        embedding_written=embedding_written,
        replaced_existing=False,
        audit=audit,
    )
