"""Vector chat (pgvector cosine + Groq)."""

from __future__ import annotations

import json
import logging
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.api.patients import resolve_patient_id
from app.db import get_conn
from app.embeddings import embed_query_text
from app.llm import groq_chat_complete
from app.schemas.api_chat import ChatCitation, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _excerpt(summary: str | None, conversation_text: str, max_len: int = 900) -> str:
    sm = (summary or "").strip()
    cx = (conversation_text or "").strip()
    merged = ""
    if sm:
        merged = sm
    if cx:
        sep = "\n---\n" if merged else ""
        merged += sep + cx
    merged = merged.replace("\r\n", "\n").strip()
    if len(merged) <= max_len:
        return merged
    return merged[: max_len - 3] + "..."


def _lc_block(raw) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        serialized = json.dumps(raw, indent=2, default=str)
    elif isinstance(raw, str):
        try:
            serialized = json.dumps(json.loads(raw), indent=2, default=str)
        except json.JSONDecodeError:
            serialized = raw
    else:
        serialized = str(raw)
    cap = 4000
    if len(serialized) > cap:
        return serialized[: cap - 3] + "..."
    return serialized


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> ChatResponse:
    if body.domain != body.domain.strip() or not body.domain:
        raise HTTPException(status_code=400, detail="Invalid domain.")

    indexed = await conn.fetchval(
        """
        SELECT EXISTS (
          SELECT 1 FROM notes
          WHERE domain = $1 AND embedding IS NOT NULL
          LIMIT 1
        )
        """,
        body.domain,
    )
    if not indexed:
        raise HTTPException(
            status_code=503,
            detail=(
                "No embeddings in the database for this domain. Load OpenAI embeddings with "
                "scribe-load-corpus --embed after setting OPENAI_API_KEY."
            ),
        )

    patient_uuid = None
    if body.patient_id:
        patient_uuid = await resolve_patient_id(conn, body.patient_id)

    longitudinal = None
    if patient_uuid is not None:
        row_lc = await conn.fetchrow(
            """
            SELECT longitudinal_context
            FROM notes
            WHERE patient_id = $1::uuid AND longitudinal_context IS NOT NULL
            ORDER BY session_date DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            patient_uuid,
        )
        if row_lc and row_lc["longitudinal_context"] is not None:
            longitudinal = _lc_block(row_lc["longitudinal_context"])

    try:
        _, vec_lit = await embed_query_text(body.message)
    except RuntimeError as e:
        logger.warning("embedding_unavailable %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e

    rows = await conn.fetch(
        """
        SELECT n.id AS note_id,
               n.external_encounter_id,
               COALESCE((n.structured_note->>'summary'), '') AS summary,
               COALESCE(n.conversation_text, '') AS conversation_text,
               (n.embedding <=> $1::vector)::float AS distance,
               ((1::float - (n.embedding <=> $1::vector)))::float AS cosine_sim,
               COALESCE(length(n.conversation_text), 0) AS cx_len,
               COALESCE(length(n.structured_note::text), 0) AS sn_len,
               COALESCE(EXTRACT(epoch FROM COALESCE(n.session_date::timestamptz, n.created_at))::bigint, 0) AS sess
        FROM notes n
        WHERE n.domain = $4
          AND n.embedding IS NOT NULL
          AND ($2::uuid IS NULL OR n.patient_id = $2::uuid)
        ORDER BY n.embedding <=> $1::vector ASC, cx_len DESC, sn_len DESC, sess DESC NULLS LAST
        LIMIT $3
        """,
        vec_lit,
        patient_uuid,
        body.top_k,
        body.domain,
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Retrieval returned no chunks (check patient scope and corpus).",
        )

    citations = [
        ChatCitation(
            note_id=r["note_id"],
            similarity=float(r["cosine_sim"]),
            excerpt=_excerpt(r["summary"] or "", r["conversation_text"] or ""),
            summary=(r["summary"] or "").strip() or None,
            external_encounter_id=r["external_encounter_id"],
        )
        for r in rows
    ]

    blocks = []
    for r in rows:
        bid = str(r["note_id"])
        sm = (r["summary"] or "").strip()
        hdr = sm[:240] + ("..." if len(sm) > 240 else "") if sm else "(no summary)"
        body_txt = _excerpt(r["summary"], r["conversation_text"] or "", max_len=1200)
        blocks.append(
            f"[note:{bid}] encounter={r['external_encounter_id']} | summary: {hdr}\n{body_txt}"
        )
    corpus = "\n\n".join(blocks)

    lc_section = ""
    if longitudinal:
        lc_section = (
            "\n\nPatient longitudinal context (frozen dataset bundle; cite notes when applicable):\n"
            f"{longitudinal}\n"
        )

    sys_prompt = (
        "You answer using ONLY the provided clinical note excerpts and optional longitudinal bundle. "
        "If insufficient evidence, say you cannot tell from these notes."
        ' Cite evidence as bracketed ids like [note:<uuid>] matching the excerpts.'
        " Do not invent patient facts."
        + lc_section
        + "\n\n---NOTE EXCERPTS---\n"
        + corpus
    )

    msg_list: list[dict[str, str]] = [{"role": "system", "content": sys_prompt}]
    for turn in body.conversation[-12:]:
        msg_list.append({"role": turn.role, "content": turn.content})
    msg_list.append({"role": "user", "content": body.message.strip()})

    try:
        answer = await groq_chat_complete(msg_list)
    except RuntimeError as e:
        logger.warning("llm_unavailable %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e

    return ChatResponse(answer=answer, citations=citations)

