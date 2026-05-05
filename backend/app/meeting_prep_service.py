"""Build patient meeting-prep bundles and Groq prompts (Phase-1 HTML parity)."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

import asyncpg


MEETING_PREP_PROMPT_VERSION = "scribe-meeting-prep-1"


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


def _longitudinal_richness_score(lc: dict[str, object]) -> int:
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


def _json_compact(obj: object, *, max_chars: int) -> str:
    raw = json.dumps(obj, indent=2, default=str, ensure_ascii=False)
    raw = raw.strip()
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 3] + "..."


async def notes_fingerprint(conn: asyncpg.Connection, patient_id: UUID) -> str:
    row = await conn.fetchrow(
        """
        SELECT COUNT(*)::int AS c,
               COALESCE(MAX(session_date)::text, '') AS s,
               COALESCE(MAX(created_at)::text, '') AS t
        FROM notes
        WHERE patient_id = $1::uuid
        """,
        patient_id,
    )
    assert row is not None
    return f"{row['c']}|{row['s']}|{row['t']}"


async def meeting_prep_context_bundle(
    conn: asyncpg.Connection,
    *,
    patient_id: UUID,
    domain: str,
) -> tuple[str, dict[str, Any]] | None:
    """Return (fingerprint, facts dict) used for prompting + cache invalidation."""

    prow = await conn.fetchrow(
        """
        SELECT id, external_id, name, metadata
        FROM patients
        WHERE id = $1::uuid AND domain = $2
        """,
        patient_id,
        domain,
    )
    if not prow:
        return None

    meta = _coerce_json_obj(prow["metadata"])
    meta_public = {
        "name": prow["name"],
        "external_id": prow["external_id"],
        "sex": meta.get("sex"),
        "birthdate": meta.get("birthdate"),
        "primary_specialty": meta.get("primary_specialty"),
        "display_name": meta.get("display_name"),
    }

    lng_rows = await conn.fetch(
            """
            SELECT longitudinal_context
            FROM notes
            WHERE patient_id = $1::uuid
              AND domain = $2
              AND longitudinal_context IS NOT NULL
            ORDER BY session_date DESC NULLS LAST, created_at DESC
            LIMIT 50
            """ ,
            patient_id,
            domain,
        )

    note_rows = await conn.fetch(
            """
            SELECT id AS note_id,
                   session_date,
                   specialty,
                   structured_note->>'summary' AS summary,
                   left(structured_note->>'full_note', 1200) AS full_note_excerpt
            FROM notes
            WHERE patient_id = $1::uuid AND domain = $2
            ORDER BY session_date DESC NULLS LAST, created_at DESC
            LIMIT 18
            """ ,
            patient_id,
            domain,
        )

    lng = _pick_richest_longitudinal(lng_rows)

    visits: list[dict[str, Any]] = []
    for r in note_rows:
        sd = r["session_date"]
        if isinstance(sd, datetime):
            sd_out = sd.date().isoformat()
        elif isinstance(sd, date):
            sd_out = sd.isoformat()
        else:
            sd_out = str(sd) if sd is not None else None
        visits.append(
            {
                "note_id": str(r["note_id"]),
                "session_date": sd_out,
                "specialty": r["specialty"],
                "summary": (r["summary"] or "").strip(),
                "full_note_excerpt": (r["full_note_excerpt"] or "").strip(),
            }
        )

    fp = await notes_fingerprint(conn, patient_id)
    facts: dict[str, Any] = {
        "patient": meta_public,
        "longitudinal_context": lng,
        "recent_encounters_newest_first": visits,
    }
    return fp, facts





def deterministic_meeting_prep_summary(facts: dict[str, Any]) -> str:
    """Local prep blurb when Groq is unavailable (missing key, quota, or transport errors)."""

    patient = facts.get("patient") if isinstance(facts.get("patient"), dict) else {}
    name = str(patient.get("display_name") or patient.get("name") or "Patient").strip() or "Patient"
    ext = str(patient.get("external_id") or "").strip()
    sex = patient.get("sex")
    bd = patient.get("birthdate")
    spec = patient.get("primary_specialty")

    header_bits: list[str] = []
    if ext:
        header_bits.append(f"id {ext}")
    if sex:
        header_bits.append(f"sex {sex}")
    if bd:
        header_bits.append(f"DOB {bd}")
    if spec:
        header_bits.append(f"noted specialty {spec}")
    header_suffix = f" ({', '.join(header_bits)})" if header_bits else ""

    p1 = (
        f"{name}{header_suffix} — chart prep (offline). "
        "This text is assembled from stored encounter rows and longitudinal JSON; it is not LLM-polished."
    )

    visits_raw = facts.get("recent_encounters_newest_first")
    visits = visits_raw if isinstance(visits_raw, list) else []
    lines: list[str] = []
    for v in visits[:14]:
        if not isinstance(v, dict):
            continue
        sd = str(v.get("session_date") or "—").strip()
        sp = str(v.get("specialty") or "Clinical").strip()
        summ = str(v.get("summary") or "").strip()
        ex = str(v.get("full_note_excerpt") or "").strip()
        body = summ if summ else ex
        if len(body) > 320:
            body = body[:317].rstrip() + "..."
        lines.append(f"- {sd} ({sp}): {body or 'No synopsis in structured_note.'}")

    p2 = "Recent documented encounters (newest first):" + '\n\n' + ('\n'.join(lines) if lines else "_No encounter rows returned.")

    lng = facts.get("longitudinal_context")
    if isinstance(lng, dict) and lng:
        pvs = lng.get("prior_visits")
        n = len(pvs) if isinstance(pvs, list) else 0
        p3 = (
            f"A longitudinal context bundle is on file ({n} prior visit rows in the capped window). "
            "Use the Sources tab on the patient chart for citation-style priors."
        )
    else:
        p3 = "No longitudinal JSON was attached to notes for this patient (or the bundle was empty after parsing)."

    p4 = (
        "NOTE: Groq is not configured or the model call failed — set `GROQ_API_KEY` in `backend/.env` "
        "and restart the API to enable AI-polished pre-meeting summaries."
    )

    return ('\n\n').join([p1, p2, p3, p4])


def meeting_prep_messages(facts: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You are a clinical documentation assistant for a synthetic demo corpus. "
        "Write a concise pre-visit / chart prep summary for the clinician in **2–4 short paragraphs** "
        "using ONLY the JSON facts provided. "
        "Highlight problems, trajectory, and what changed recently when evidence exists. "
        "If facts are thin, say so explicitly. "
        "Do not invent patient identifiers, MRN, phone numbers, or unsupported diagnoses. "
        "Do not output JSON — plain professional English only."
    )
    user = "Facts JSON (ground truth):\n" + _json_compact(facts, max_chars=28_000) + "\n\nReturn the prep summary now."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
