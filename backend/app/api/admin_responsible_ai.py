"""Admin APIs for Responsible AI Control Center (metrics + audit queries)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.db import get_conn
from app.responsible_ai.dashboard_derived import (
    SAFETY_FLAG_TAXONOMY,
    count_citations,
    count_retrieved_sources,
    derive_latency_display,
    derive_risk_tier,
    derive_run_mode,
    merge_safety_counts,
    parse_safety_flags,
)


router = APIRouter(prefix="/admin/responsible-ai", tags=["admin-responsible-ai"])


def _settings_or_404() -> None:
    settings = get_settings()
    if not settings.responsible_ai_admin_enabled:
        raise HTTPException(status_code=404, detail="Responsible AI admin API is disabled.")
    return None


@router.get("/metrics")
async def metrics(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    days: int = Query(default=14, ge=1, le=366),
) -> dict[str, Any]:
    _settings_or_404()
    total = await conn.fetchval("SELECT COUNT(*)::bigint FROM ai_interactions")
    ok = await conn.fetchval(
        "SELECT COUNT(*)::bigint FROM ai_interactions WHERE status = $1", "success"
    )
    degraded = await conn.fetchval(
        "SELECT COUNT(*)::bigint FROM ai_interactions WHERE status = $1", "degraded"
    )
    failed = await conn.fetchval(
        "SELECT COUNT(*)::bigint FROM ai_interactions WHERE status = $1", "failed"
    )
    blocked = await conn.fetchval(
        "SELECT COUNT(*)::bigint FROM ai_interactions WHERE status = $1", "blocked"
    )
    total_i = int(total or 0)
    ok_i = int(ok or 0)
    avg_lat = await conn.fetchval(
        "SELECT AVG(latency_ms)::float FROM ai_interactions WHERE latency_ms IS NOT NULL"
    )
    flagged = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint FROM ai_interactions
        WHERE jsonb_typeof(COALESCE(safety_flags_json, '[]'::jsonb)) = 'array'
          AND jsonb_array_length(COALESCE(safety_flags_json, '[]'::jsonb)) > 0
        """
    )

    chat_mp = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint FROM ai_interactions
        WHERE interaction_type IN ('chat','meeting_prep')
          AND (
            (citations_json IS NOT NULL AND jsonb_array_length(COALESCE(citations_json::jsonb, '[]'::jsonb)) > 0)
            OR (retrieved_sources_json IS NOT NULL AND retrieved_sources_json::jsonb ? 'retrieved_note_ids'
                AND jsonb_array_length(COALESCE(retrieved_sources_json::jsonb -> 'retrieved_note_ids', '[]'::jsonb)) > 0)
          )
        """
    )
    cov_den = await conn.fetchval(
        "SELECT COUNT(*)::bigint FROM ai_interactions WHERE interaction_type IN ('chat','meeting_prep')"
    )
    cov_num = int(chat_mp or 0)
    cov_den_i = int(cov_den or 0)
    citation_coverage = (cov_num / cov_den_i) if cov_den_i else 0.0

    hr = await conn.fetchval(
        """
        SELECT COUNT(*)::bigint FROM ai_interactions
        WHERE interaction_type = 'note_generation'
           OR (safety_flags_json::text ILIKE '%human%')
        """
    )

    by_type_rows = await conn.fetch(
        """
        SELECT interaction_type AS t, COUNT(*)::bigint AS c FROM ai_interactions GROUP BY interaction_type
        """
    )
    by_type = {r["t"]: int(r["c"]) for r in by_type_rows}

    by_status = {
        "success": ok_i,
        "degraded": int(degraded or 0),
        "blocked": int(blocked or 0),
        "failed": int(failed or 0),
    }

    since = datetime.now(timezone.utc) - timedelta(days=days)
    ts_rows = await conn.fetch(
        """
        SELECT date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS d,
               SUM(CASE WHEN interaction_type = 'chat' THEN 1 ELSE 0 END)::int AS chat,
               SUM(CASE WHEN interaction_type = 'meeting_prep' THEN 1 ELSE 0 END)::int AS meeting_prep,
               SUM(CASE WHEN interaction_type = 'note_generation' THEN 1 ELSE 0 END)::int AS note_generation
        FROM ai_interactions
        WHERE created_at >= $1
        GROUP BY 1
        ORDER BY 1 ASC
        """,
        since,
    )
    time_series = [
        {
            "date": str(r["d"]),
            "chat": r["chat"],
            "meeting_prep": r["meeting_prep"],
            "note_generation": r["note_generation"],
        }
        for r in ts_rows
    ]

    success_rate = (ok_i / total_i) if total_i else 0.0

    avg_lat_gen = await conn.fetchval(
        '''
        SELECT AVG(latency_ms)::float FROM ai_interactions
        WHERE latency_ms IS NOT NULL
          AND NOT (
            interaction_type = 'meeting_prep'
            AND COALESCE((governance_json::jsonb ->> 'cached')::boolean, false) = true
            AND latency_ms <= 5
          )
        '''
    )

    sf_rows = await conn.fetch(
        '''
        SELECT safety_flags_json FROM ai_interactions WHERE safety_flags_json IS NOT NULL
        '''
    )
    raw_sf: dict[str, int] = {}
    for r in sf_rows:
        raw = r["safety_flags_json"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                continue
        if not isinstance(raw, list):
            continue
        for flag in raw:
            if isinstance(flag, dict) and flag.get("code"):
                code = str(flag["code"])
                raw_sf[code] = raw_sf.get(code, 0) + 1
    merged_sf = merge_safety_counts(raw_sf)
    safety_breakdown = [
        {"code": code, "label": label, "count": merged_sf.get(code, 0)}
        for code, label in SAFETY_FLAG_TAXONOMY
    ]

    trust_context = {
        "phi_redaction_enabled": True,
        "prompt_and_model_traceability": True,
        "audit_storage": "postgres_ai_interactions",
        "safety_checks_enabled": True,
    }

    return {
        "summary": {
            "total_interactions": total_i,
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": int(avg_lat or 0),
            "avg_latency_ms_generated": int(avg_lat_gen or 0),
            "citation_coverage": round(float(citation_coverage), 4),
            "safety_flag_count": int(flagged or 0),
            "human_review_required": int(hr or 0),
            "clinical_review_signals": int(hr or 0),
        },
        "by_type": by_type,
        "by_status": by_status,
        "time_series": time_series,
        "safety_breakdown": safety_breakdown,
        "trust_context": trust_context,
    }


@router.get("/interactions")
async def list_interactions(
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    interaction_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
) -> dict[str, Any]:
    _settings_or_404()
    clauses: list[str] = []
    args: list[Any] = []
    if interaction_type:
        clauses.append(f"interaction_type = ${len(args) + 1}")
        args.append(interaction_type)
    if status:
        clauses.append(f"status = ${len(args) + 1}")
        args.append(status)
    if patient_id:
        clauses.append(f"patient_id ILIKE ${len(args) + 1}")
        args.append(f"%{patient_id}%")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    lim_idx = len(args) + 1
    off_idx = len(args) + 2
    rows = await conn.fetch(
        f"""
        SELECT id, request_id, interaction_type, patient_id, note_id,
               model_provider, model_name, prompt_version, status, latency_ms,
               created_at, governance_json, citations_json, retrieved_sources_json,
               safety_flags_json, output_redacted_preview
        FROM ai_interactions
        {where}
        ORDER BY created_at DESC
        LIMIT ${lim_idx} OFFSET ${off_idx}
        """,
        *args,
        limit,
        offset,
    )
    items = []
    for r in rows:
        gov = r["governance_json"]
        cit_j = r["citations_json"]
        src_j = r["retrieved_sources_json"]
        sflags = r["safety_flags_json"]
        c_count = count_citations(cit_j)
        s_count = count_retrieved_sources(src_j)
        flags = parse_safety_flags(sflags)
        lat_ms = int(r["latency_ms"]) if r["latency_ms"] is not None else None
        lat_disp = derive_latency_display(
            interaction_type=r["interaction_type"],
            governance_json=gov,
            latency_ms=lat_ms,
        )
        risk = derive_risk_tier(
            interaction_type=r["interaction_type"],
            status=r["status"],
            citation_count=c_count,
            source_count=s_count,
            safety_flags=flags,
            governance_json=gov,
        )
        prev = r["output_redacted_preview"]
        if isinstance(prev, str) and len(prev) > 320:
            prev = prev[:320] + "…"
        items.append(
            {
                "id": str(r["id"]),
                "request_id": r["request_id"],
                "interaction_type": r["interaction_type"],
                "patient_id": r["patient_id"],
                "note_id": r["note_id"],
                "model_provider": r["model_provider"],
                "model_name": r["model_name"],
                "prompt_version": r["prompt_version"],
                "status": r["status"],
                "latency_ms": lat_ms,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "citation_count": c_count,
                "source_count": s_count,
                "run_mode": derive_run_mode(
                    interaction_type=r["interaction_type"],
                    governance_json=gov,
                ),
                "latency_display": lat_disp,
                "risk_tier": risk,
                "output_preview": prev,
            }
        )
    total = await conn.fetchval(f"SELECT COUNT(*)::bigint FROM ai_interactions {where}", *args)
    return {"items": items, "total": int(total or 0), "limit": limit, "offset": offset}


@router.get("/interactions/{interaction_id}")
async def get_interaction(
    interaction_id: UUID,
    conn: Annotated[asyncpg.Connection, Depends(get_conn)],
) -> dict[str, Any]:
    _settings_or_404()
    row = await conn.fetchrow(
        """
        SELECT * FROM ai_interactions WHERE id = $1::uuid
        """,
        interaction_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    def _json(val):
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        return val

    out = {k: row[k] for k in row.keys()}
    out["id"] = str(out["id"])
    for key in (
        "retrieved_sources_json",
        "citations_json",
        "safety_flags_json",
        "governance_json",
    ):
        out[key] = _json(out.get(key))
    if out.get("created_at"):
        out["created_at"] = out["created_at"].isoformat()
    return out


@router.get("/safety-flags")
async def safety_flags(conn: Annotated[asyncpg.Connection, Depends(get_conn)]) -> dict[str, Any]:
    _settings_or_404()
    rows = await conn.fetch(
        """
        SELECT safety_flags_json FROM ai_interactions WHERE safety_flags_json IS NOT NULL
        """
    )
    counts: dict[str, int] = {}
    for r in rows:
        raw = r["safety_flags_json"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                continue
        if isinstance(raw, list):
            for flag in raw:
                if isinstance(flag, dict) and flag.get("code"):
                    code = str(flag["code"])
                    counts[code] = counts.get(code, 0) + 1
    merged = merge_safety_counts(counts)
    breakdown = [
        {"code": code, "label": label, "count": merged.get(code, 0)}
        for code, label in SAFETY_FLAG_TAXONOMY
    ]
    return {"by_code": merged, "breakdown": breakdown}


@router.get("/model-usage")
async def model_usage(conn: Annotated[asyncpg.Connection, Depends(get_conn)]) -> dict[str, Any]:
    _settings_or_404()
    rows = await conn.fetch(
        """
        SELECT model_provider, model_name,
               COUNT(*)::bigint AS runs,
               AVG(latency_ms)::float AS avg_latency_ms,
               SUM(CASE WHEN status IN ('failed','blocked') THEN 1 ELSE 0 END)::bigint AS failures
        FROM ai_interactions
        GROUP BY model_provider, model_name
        ORDER BY runs DESC
        """
    )
    items = []
    for r in rows:
        runs = int(r["runs"])
        fails = int(r["failures"])
        items.append(
            {
                "model_provider": r["model_provider"],
                "model_name": r["model_name"],
                "runs": runs,
                "avg_latency_ms": int(r["avg_latency_ms"] or 0),
                "failure_rate": (fails / runs) if runs else 0.0,
            }
        )
    return {"items": items}
