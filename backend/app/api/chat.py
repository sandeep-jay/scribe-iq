"""Vector RAG chat over clinical note embeddings (pgvector) + Groq completion.

Flow (high level): validate domain -> ensure embeddings exist for domain -> optional patient scope
-> embed user query -> retrieve top-k chunks -> build prompt -> Groq -> safety checks -> audit row.

Logging policy: use ``logger.info`` for milestones you should see in normal ops; use ``logger.debug``
for branch/detail checkpoints when ``LOG_LEVEL=DEBUG``. Never log raw clinical text here; counts,
ids, and timings only.
"""

from __future__ import annotations

import json

import structlog
import asyncpg
from fastapi import APIRouter, HTTPException, Request

from app.api.patients import resolve_patient_id
from app.config import get_settings
from app.embeddings import embed_query_text
from app.llm import groq_chat_complete
from app.request_id import get_request_id
from app.responsible_ai.audit_logger import insert_ai_interaction
from app.responsible_ai.hashes import sha256_hex
from app.responsible_ai.prompt_registry import CHAT_RAG_V1
from app.responsible_ai.redaction import redact_preview
from app.responsible_ai.safety_checks import aggregate_safety_status, evaluate_chat
from app.responsible_ai.source_trace import trace_from_chat_rows
from app.schemas.api_chat import ChatAuditBlock, ChatCitation, ChatRequest, ChatResponse

logger = structlog.get_logger(__name__)

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
    request: Request,
    body: ChatRequest,
) -> ChatResponse:
    settings = get_settings()
    req_id = get_request_id(request)
    pool: asyncpg.Pool = request.app.state.db_pool

    logger.info(
        "chat_started",
        request_id=req_id,
        domain=body.domain,
        top_k=body.top_k,
        patient_id_set=bool(body.patient_id),
        conversation_turns=len(body.conversation),
    )

    if body.domain != body.domain.strip() or not body.domain:
        logger.warning("chat_domain_invalid", request_id=req_id, domain_repr=repr(body.domain)[:120])
        raise HTTPException(status_code=400, detail="Invalid domain.")

    patient_uuid = None
    longitudinal = None
    async with pool.acquire() as conn:
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
        logger.debug("chat_embeddings_index_checked", request_id=req_id, domain=body.domain, indexed=bool(indexed))

        if not indexed:
            logger.warning("chat_no_embeddings_for_domain", request_id=req_id, domain=body.domain)
            raise HTTPException(
                status_code=503,
                detail=(
                    "No embeddings in the database for this domain. Load OpenAI embeddings with "
                    "scribe-load-corpus --embed after setting OPENAI_API_KEY."
                ),
            )

        if body.patient_id:
            patient_uuid = await resolve_patient_id(conn, body.patient_id)
            logger.debug("chat_patient_resolved", request_id=req_id, patient_id_param_set=True)
        else:
            logger.debug("chat_patient_scope_global", request_id=req_id, patient_id_param_set=False)

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
                logger.debug("chat_longitudinal_loaded", request_id=req_id, has_longitudinal=True)
            else:
                logger.debug("chat_longitudinal_missing", request_id=req_id, has_longitudinal=False)

    try:
        _, vec_lit = await embed_query_text(body.message)
        logger.debug("chat_query_embedded", request_id=req_id, domain=body.domain)
    except RuntimeError as e:
        logger.warning("embedding_unavailable", request_id=req_id, error=str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e

    async with pool.acquire() as conn:
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

    logger.info(
        "chat_retrieval_complete",
        request_id=req_id,
        domain=body.domain,
        chunk_count=len(rows),
        patient_scoped=patient_uuid is not None,
    )

    if not rows:
        logger.warning("chat_retrieval_empty", request_id=req_id, domain=body.domain, patient_scoped=patient_uuid is not None)
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

    logger.debug(
        "chat_llm_call_started",
        request_id=req_id,
        provider=settings.llm_provider,
        model=settings.groq_chat_model,
        prompt_chars=len(sys_prompt),
        user_message_chars=len(body.message.strip()),
    )
    try:
        groq_res = await groq_chat_complete(msg_list)
    except RuntimeError as e:
        logger.warning("llm_unavailable", request_id=req_id, error=str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e

    answer = groq_res.text
    logger.info(
        "chat_llm_succeeded",
        request_id=req_id,
        model=groq_res.model,
        latency_ms=groq_res.latency_ms,
        prompt_tokens=groq_res.prompt_tokens,
        completion_tokens=groq_res.completion_tokens,
        citation_count=len(citations),
    )
    trace_payload = trace_from_chat_rows(
        [{"note_id": r["note_id"], "cosine_sim": float(r["cosine_sim"])} for r in rows]
    )
    citations_payload = [{"note_id": str(c.note_id), "similarity": c.similarity} for c in citations]
    safety_flags = evaluate_chat(answer=answer, citations_count=len(citations))
    safety_status = aggregate_safety_status(safety_flags)
    sys_hash = sha256_hex(sys_prompt)
    inp_hash = sha256_hex(body.message.strip())
    out_hash = sha256_hex(answer)
    pid_str = str(patient_uuid) if patient_uuid else None

    async with pool.acquire() as conn:
        interaction_id = await insert_ai_interaction(
            conn,
            request_id=req_id,
            interaction_type="chat",
            patient_id=pid_str,
            note_id=None,
            model_provider=settings.llm_provider,
            model_name=groq_res.model,
            prompt_version=CHAT_RAG_V1,
            system_prompt_hash=sys_hash,
            input_hash=inp_hash,
            output_hash=out_hash,
            input_redacted_preview=redact_preview(body.message),
            output_redacted_preview=redact_preview(answer),
            retrieved_sources_json=trace_payload,
            citations_json=citations_payload,
            safety_flags_json=safety_flags,
            governance_json={"prompt_version": CHAT_RAG_V1},
            latency_ms=groq_res.latency_ms,
            input_tokens=groq_res.prompt_tokens,
            output_tokens=groq_res.completion_tokens,
            status="success",
            error_message=None,
        )

    logger.info(
        "chat_audit_persisted",
        request_id=req_id,
        interaction_id=interaction_id,
        safety_status=safety_status,
    )

    return ChatResponse(
        answer=answer,
        citations=citations,
        audit=ChatAuditBlock(
            interaction_id=interaction_id,
            model=groq_res.model,
            prompt_version=CHAT_RAG_V1,
            source_count=len(citations),
            safety_status=safety_status,
            latency_ms=groq_res.latency_ms,
        ),
    )

