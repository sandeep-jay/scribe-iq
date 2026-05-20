"""Patient read endpoints (T4) and chart utilities (meeting prep, stats).

Meeting prep combines cached Postgres summaries with optional Groq generation. Logs use structured
events: ``INFO`` for cache hits and generation outcomes, ``DEBUG`` for branch decisions, ``WARNING``
for expected degradations (e.g., Groq unavailable with deterministic fallback). Do not log raw chart text.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.request_id import get_request_id
from app.db import get_conn
from app.config import get_settings
from app.llm import chat_complete
from app.llm.errors import LlmConfigurationError, LlmProviderError

import structlog

logger = structlog.get_logger(__name__)

from app.meeting_prep_service import (
    MEETING_PREP_PROMPT_VERSION,
    deterministic_meeting_prep_summary,
    meeting_prep_context_bundle,
    meeting_prep_messages,
    notes_fingerprint,
)

from app.responsible_ai.audit_logger import insert_ai_interaction
from app.responsible_ai.hashes import sha256_hex
from app.responsible_ai.redaction import redact_preview
from app.responsible_ai.safety_checks import aggregate_safety_status, evaluate_meeting_prep
from app.responsible_ai.source_trace import trace_from_meeting_prep_visits
from app.schemas.api_patients import (
    CorpusPatientStats,
    MeetingPrepAiAudit,
    MeetingPrepResponse,
    NotePreview,
    PaginatedPatients,
    PatientDetail,
    PatientListItem,
)

import json


def _coerce_json_obj(value) -> dict[str, object]:
    """asyncpg may return json/jsonb as str depending on server settings."""
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


def _longitudinal_richness_score(lc: dict[str, object]) -> int:
    """Prefer richer longitudinal bundles when many encounters omit meds in pure prior-history slices."""

    score = 0

    meds_union_raw = lc.get("medications_union")
    score += len(meds_union_raw) if isinstance(meds_union_raw, list) else 0

    cur_raw = lc.get("current_encounter_snapshot")
    if isinstance(cur_raw, dict):
        for key in ("conditions", "medications"):
            vals = cur_raw.get(key)
            score += len(vals) if isinstance(vals, list) else 0

    pvs_raw = lc.get("prior_visits")
    if isinstance(pvs_raw, list):
        for pv_raw in pvs_raw:
            if not isinstance(pv_raw, dict):
                continue
            conds = pv_raw.get("conditions")
            meds = pv_raw.get("medications")
            obs = pv_raw.get("key_observations")
            reason_val = pv_raw.get("reason")
            score += len(conds) if isinstance(conds, list) else 0
            score += len(meds) if isinstance(meds, list) else 0
            score += len(obs) if isinstance(obs, list) else 0
            reason = reason_val.strip() if isinstance(reason_val, str) else ""
            if reason and reason.casefold() != "not documented".casefold():
                score += 1
    return score


def _longitudinal_med_hints(lng_rows: list[asyncpg.Record], *, limit: int = 48) -> list[str]:
    """Union medication labels recorded in longitudinal payloads (prior visits + anchored encounter)."""

    seen: set[str] = set()
    hints: list[str] = []

    def push_list(raw_list) -> bool:
        """Return True if caller should stop (cap reached)."""
        if not isinstance(raw_list, list):
            return False
        for raw in raw_list:
            label = str(raw).strip()
            if not label or label in seen:
                continue
            seen.add(label)
            hints.append(label)
            if len(hints) >= limit:
                return True
        return False

    for row in lng_rows:
        lc = _coerce_json_obj(row["longitudinal_context"])
        if not lc:
            continue

        if push_list(lc.get("medications_union")):
            return hints[:limit]

        cur = lc.get("current_encounter_snapshot")
        if isinstance(cur, dict):
            if push_list(cur.get("medications")):
                return hints[:limit]

        visits = lc.get("prior_visits")
        if isinstance(visits, list):
            for pv_raw in visits:
                if not isinstance(pv_raw, dict):
                    continue
                if push_list(pv_raw.get("medications")):
                    return hints[:limit]

        if len(hints) >= limit:
            break

    return hints[:limit]


def _pick_richest_longitudinal(lng_rows: list[asyncpg.Record]) -> dict[str, object] | None:
    best: dict[str, object] | None = None
    best_score = -1
    for row in lng_rows:
        lc = _coerce_json_obj(row["longitudinal_context"])
        if not lc:
            continue
        s = _longitudinal_richness_score(lc)
        if s > best_score:
            best_score = s
            best = lc
    return best


router = APIRouter(tags=["patients"])


async def resolve_patient_id(conn: asyncpg.Connection, patient_id: str) -> UUID:
    try:
        uid = UUID(patient_id)
    except ValueError:
        row = await conn.fetchrow("SELECT id FROM patients WHERE external_id = $1", patient_id)
        if not row:
            raise HTTPException(status_code=404, detail="Patient not found") from None
        return row["id"]

    row = await conn.fetchrow("SELECT id FROM patients WHERE id = $1::uuid", uid)
    if row:
        return row["id"]
    row = await conn.fetchrow("SELECT id FROM patients WHERE external_id = $1", patient_id)
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return row["id"]


@router.get("/patients", response_model=PaginatedPatients)
async def list_patients(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    domain: str = Query(default="clinical"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PaginatedPatients:
    total_row = await conn.fetchrow(
        "SELECT COUNT(*)::int AS c FROM patients WHERE domain = $1",
        domain,
    )
    assert total_row is not None
    rows = await conn.fetch(
        """
        SELECT p.id,
               p.external_id,
               p.name,
               p.metadata,
               COUNT(n.id)::int AS note_count,
               MAX(n.session_date) AS last_session_date,
               COALESCE(BOOL_OR(n.longitudinal_context IS NOT NULL), false) AS has_longitudinal,
               MAX(n.specialty) AS last_specialty
        FROM patients p
        LEFT JOIN notes n
          ON n.patient_id = p.id AND n.domain = $1
        WHERE p.domain = $1
        GROUP BY p.id
        ORDER BY p.name ASC
        LIMIT $2 OFFSET $3
        """ ,
        domain,
        limit,
        offset,
    )
    assert total_row is not None

    patients = [
        PatientListItem(
            id=r["id"],
            external_id=r["external_id"],
            name=r["name"],
            metadata=_coerce_json_obj(r["metadata"]),
            note_count=r["note_count"],
            last_session_date=r["last_session_date"],
            has_longitudinal=bool(r["has_longitudinal"]),
            last_specialty=r["last_specialty"],
        )
        for r in rows
    ]

    return PaginatedPatients(patients=patients, total=total_row["c"], limit=limit, offset=offset)




@router.get("/patients/stats", response_model=CorpusPatientStats)
async def patient_corpus_stats(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    domain: str = Query(default="clinical"),
) -> CorpusPatientStats:
    row = await conn.fetchrow(
        """
        SELECT
          (SELECT COUNT(*)::int FROM patients WHERE domain = $1) AS pc,
          (SELECT COUNT(*)::int FROM notes WHERE domain = $1) AS nc
        """,
        domain,
    )
    assert row is not None
    return CorpusPatientStats(domain=domain, total_patients=row["pc"], total_notes=row["nc"])


@router.get("/patients/{patient_id}/meeting-prep", response_model=MeetingPrepResponse)
async def get_meeting_prep(
    request: Request,
    patient_id: str,
    domain: str = Query(default="clinical"),
    refresh: bool = Query(default=False, description="Force regeneration even if cache is fresh."),
) -> MeetingPrepResponse:
    settings = get_settings()
    req_id = get_request_id(request)
    pool: asyncpg.Pool = request.app.state.db_pool
    logger.info(
        "meeting_prep_started",
        request_id=req_id,
        domain=domain,
        refresh=bool(refresh),
    )

    if not settings.meeting_prep_enabled:
        logger.warning("meeting_prep_disabled", request_id=req_id)
        raise HTTPException(
            status_code=403,
            detail="Meeting prep disabled. Set MEETING_PREP_ENABLED=true in backend/.env.",
        )

    pid: UUID
    fp: str
    facts: dict
    visit_ids: list[str]
    trace_payload: dict

    async with pool.acquire() as conn:
        pid = await resolve_patient_id(conn, patient_id)
        logger.debug("meeting_prep_patient_resolved", request_id=req_id, patient_uuid=str(pid))

        if not refresh:
            logger.debug("meeting_prep_cache_lookup", request_id=req_id, domain=domain)
            cached = await conn.fetchrow(
                """
                SELECT summary_text, source_fingerprint, generated_at, model, prompt_version
                FROM patient_meeting_prep
                WHERE patient_id = $1::uuid AND domain = $2
                """,
                pid,
                domain,
            )
            if cached:
                current_fp = await notes_fingerprint(conn, pid)
                if cached["source_fingerprint"] == current_fp:
                    mdl = str(cached["model"] or "")
                    degraded = mdl == "deterministic-fallback"
                    logger.info(
                        "meeting_prep_cache_hit",
                        request_id=req_id,
                        degraded=degraded,
                        model=mdl,
                    )
                    return MeetingPrepResponse(
                        patient_id=pid,
                        summary=cached["summary_text"],
                        generated_at=cached["generated_at"],
                        cached=True,
                        prompt_version=cached["prompt_version"],
                        model=cached["model"],
                        degraded=degraded,
                        ai_audit=None,
                    )
                logger.info(
                    "meeting_prep_cache_stale",
                    request_id=req_id,
                    stored_fp_preview=str(cached["source_fingerprint"])[:16],
                    current_fp_preview=str(current_fp)[:16],
                )
            else:
                logger.debug("meeting_prep_cache_miss", request_id=req_id, domain=domain)

        bundle = await meeting_prep_context_bundle(conn, patient_id=pid, domain=domain)
        if bundle is None:
            logger.warning("meeting_prep_patient_not_found", request_id=req_id)
            raise HTTPException(status_code=404, detail="Patient not found")
        fp, facts = bundle

    logger.debug(
        "meeting_prep_bundle_ok",
        request_id=req_id,
        fingerprint=fp,
        visit_count=len(facts.get("recent_encounters_newest_first") or []),
    )

    visits_raw = facts.get("recent_encounters_newest_first") or []
    visit_ids = [
        str(v.get("note_id"))
        for v in visits_raw
        if isinstance(v, dict) and v.get("note_id")
    ]
    trace_payload = trace_from_meeting_prep_visits(list(visits_raw), fingerprint=fp)

    llm_ready = settings.llm_configured()
    degraded = False
    completion = None
    llm_provider_name = "deterministic"
    if llm_ready:
        logger.debug("meeting_prep_llm_configured", request_id=req_id, provider=settings.normalized_llm_provider())
        try:
            msgs = meeting_prep_messages(facts)
            logger.debug(
                "meeting_prep_llm_call_started",
                request_id=req_id,
                provider=settings.normalized_llm_provider(),
            )
            completion = await chat_complete(msgs, temperature=0.2, max_tokens=900)
            summary = completion.text
            model = completion.model or settings.groq_chat_model
            llm_provider_name = completion.provider
            pv = MEETING_PREP_PROMPT_VERSION
            logger.info(
                "meeting_prep_llm_succeeded",
                request_id=req_id,
                model=model,
                provider=llm_provider_name,
                latency_ms=completion.latency_ms,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
            )
        except (LlmConfigurationError, LlmProviderError, Exception) as e:
            logger.warning("meeting_prep_llm_unavailable", request_id=req_id, error=str(e))
            summary = deterministic_meeting_prep_summary(facts)
            model = "deterministic-fallback"
            llm_provider_name = "deterministic"
            pv = f"{MEETING_PREP_PROMPT_VERSION}-offline"
            degraded = True
    else:
        logger.info("meeting_prep_llm_not_configured", request_id=req_id)
        summary = deterministic_meeting_prep_summary(facts)
        model = "deterministic-fallback"
        llm_provider_name = "deterministic"
        pv = f"{MEETING_PREP_PROMPT_VERSION}-offline"
        degraded = True

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO patient_meeting_prep (
              patient_id, domain, summary_text, model, prompt_version, source_fingerprint, generated_at
            ) VALUES ($1::uuid, $2, $3, $4, $5, $6, now())
            ON CONFLICT (patient_id) DO UPDATE SET
              domain = EXCLUDED.domain,
              summary_text = EXCLUDED.summary_text,
              model = EXCLUDED.model,
              prompt_version = EXCLUDED.prompt_version,
              source_fingerprint = EXCLUDED.source_fingerprint,
              generated_at = now()
            """,
            pid,
            domain,
            summary,
            model,
            pv,
            fp,
        )
        row2 = await conn.fetchrow(
            "SELECT generated_at FROM patient_meeting_prep WHERE patient_id = $1::uuid",
            pid,
        )
        assert row2 is not None

        flags = evaluate_meeting_prep(summary=summary, visit_note_ids=visit_ids)
        safety_status = aggregate_safety_status(flags)
        sta = "degraded" if degraded else "success"
        inp_hash = sha256_hex(json.dumps(facts, default=str)[:60_000])
        out_hash = sha256_hex(summary)
        sys_hash = sha256_hex(f"{MEETING_PREP_PROMPT_VERSION}|meeting_prep_system")
        lat = completion.latency_ms if completion is not None else 1
        itok = completion.prompt_tokens if completion is not None else None
        otok = completion.completion_tokens if completion is not None else None
        mname = completion.model if completion is not None else model
        iid = await insert_ai_interaction(
            conn,
            request_id=req_id,
            interaction_type="meeting_prep",
            patient_id=str(pid),
            note_id=None,
            model_provider=llm_provider_name,
            model_name=mname,
            prompt_version=pv,
            system_prompt_hash=sys_hash,
            input_hash=inp_hash,
            output_hash=out_hash,
            input_redacted_preview=redact_preview(json.dumps(facts, default=str)[:8000]),
            output_redacted_preview=redact_preview(summary),
            retrieved_sources_json=trace_payload,
            citations_json=None,
            safety_flags_json=flags,
            governance_json={
                "cached": False,
                "source_fingerprint": fp,
                "degraded": degraded,
            },
            latency_ms=lat,
            input_tokens=itok,
            output_tokens=otok,
            status=sta,
            error_message=None,
        )

    ai_audit = MeetingPrepAiAudit(
        interaction_id=iid,
        cached=False,
        source_fingerprint=fp,
        prompt_version=pv,
        source_count=len(visit_ids),
        safety_status=safety_status,
    )
    logger.info(
        "meeting_prep_regenerated",
        request_id=req_id,
        degraded=degraded,
        interaction_id=ai_audit.interaction_id,
    )
    return MeetingPrepResponse(
        patient_id=pid,
        summary=summary,
        generated_at=row2["generated_at"],
        cached=False,
        prompt_version=pv,
        model=model,
        degraded=degraded,
        ai_audit=ai_audit,
    )


@router.get("/patients/{patient_id}", response_model=PatientDetail)
async def get_patient(
    patient_id: str,
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> PatientDetail:
    pid = await resolve_patient_id(conn, patient_id)

    prow = await conn.fetchrow(
            """
            SELECT id, external_id, name, metadata
            FROM patients
            WHERE id = $1::uuid
            """ ,
            pid,
        )
    assert prow is not None

    cnt_row = await conn.fetchrow(
        "SELECT COUNT(*)::int AS c FROM notes WHERE patient_id = $1::uuid",
        pid,
    )
    assert cnt_row is not None

    lng_rows = await conn.fetch(
            """
            SELECT longitudinal_context
            FROM notes
            WHERE patient_id = $1::uuid AND longitudinal_context IS NOT NULL
            ORDER BY session_date DESC NULLS LAST, created_at DESC
            LIMIT 50
            """ ,
            pid,
        )

    note_rows = await conn.fetch(
            """
            SELECT id,
                   external_encounter_id,
                   corpus_note_id,
                   session_date,
                   specialty,
                   structured_note->>'summary' AS summary,
                   (length(conversation_text) > 0) AS has_dialogue
            FROM notes
            WHERE patient_id = $1::uuid
            ORDER BY session_date DESC NULLS LAST, created_at DESC
            LIMIT 100
            """ ,
            pid,
        )

    meta = _coerce_json_obj(prow["metadata"])

    notes = [
        NotePreview(
            id=r["id"],
            external_encounter_id=r["external_encounter_id"],
            corpus_note_id=r["corpus_note_id"],
            session_date=r["session_date"],
            specialty=r["specialty"],
            summary=r["summary"],
            has_dialogue=bool(r["has_dialogue"]),
        )
        for r in note_rows
    ]

    longitudinal_med_hints = _longitudinal_med_hints(lng_rows)
    latest_longitudinal = _pick_richest_longitudinal(lng_rows)

    return PatientDetail(
        id=prow["id"],
        external_id=prow["external_id"],
        name=prow["name"],
        metadata=meta,
        note_count=int(cnt_row["c"]),
        latest_longitudinal=latest_longitudinal,
        longitudinal_medication_hints=longitudinal_med_hints,
        notes=notes,
    )
