"""Patient read endpoints (T4)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_conn
from app.config import get_settings
from app.llm import groq_chat_complete
from app.meeting_prep_service import MEETING_PREP_PROMPT_VERSION, meeting_prep_context_bundle, meeting_prep_messages
from app.schemas.api_patients import (
    CorpusPatientStats,
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
               MAX(n.session_date) AS last_session_date
        FROM patients p
        LEFT JOIN notes n
          ON n.patient_id = p.id AND n.domain = $1
        WHERE p.domain = $1
        GROUP BY p.id
        ORDER BY p.name ASC
        LIMIT $2 OFFSET $3
        """,
        domain,
        limit,
        offset,
    )

    patients = [
        PatientListItem(
            id=r["id"],
            external_id=r["external_id"],
            name=r["name"],
            metadata=_coerce_json_obj(r["metadata"]),
            note_count=r["note_count"],
            last_session_date=r["last_session_date"],
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
    patient_id: str,
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    domain: str = Query(default="clinical"),
    refresh: bool = Query(default=False, description="Force regeneration even if cache is fresh."),
) -> MeetingPrepResponse:
    settings = get_settings()
    if not settings.meeting_prep_enabled:
        raise HTTPException(
            status_code=403,
            detail="Meeting prep disabled. Set MEETING_PREP_ENABLED=true in backend/.env.",
        )

    pid = await resolve_patient_id(conn, patient_id)
    bundle = await meeting_prep_context_bundle(conn, patient_id=pid, domain=domain)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    fp, facts = bundle

    if not refresh:
        cached = await conn.fetchrow(
            """
            SELECT summary_text, source_fingerprint, generated_at, model, prompt_version
            FROM patient_meeting_prep
            WHERE patient_id = $1::uuid AND domain = $2
            """,
            pid,
            domain,
        )
        if cached and cached["source_fingerprint"] == fp:
            return MeetingPrepResponse(
                patient_id=pid,
                summary=cached["summary_text"],
                generated_at=cached["generated_at"],
                cached=True,
                prompt_version=cached["prompt_version"],
                model=cached["model"],
            )

    try:
        msgs = meeting_prep_messages(facts)
        summary = await groq_chat_complete(msgs, temperature=0.2, max_tokens=900)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    model = settings.groq_chat_model
    pv = MEETING_PREP_PROMPT_VERSION
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
    return MeetingPrepResponse(
        patient_id=pid,
        summary=summary,
        generated_at=row2["generated_at"],
        cached=False,
        prompt_version=pv,
        model=model,
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
        """,
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
        LIMIT 80
        """,
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
        """,
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
