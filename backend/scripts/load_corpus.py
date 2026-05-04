"""Load clinical_corpus_v2 JSONL (+ staging longitudinal) into Postgres (T3).

Run from repo `backend/`:

  pip install -e .
  python -m scripts.load_corpus [--truncate] [--embed]
  # or: scribe-load-corpus [--truncate] [--embed]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from psycopg2.extras import Json, execute_batch
from tqdm import tqdm

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_PREP_ROOT = REPO_ROOT / "data_prep"
if str(DATA_PREP_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_PREP_ROOT))

from utils.synthea_name_prettify import prettify_synthea_display_name, prettify_synthea_token


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _fallback_patient_label(external_id: str) -> str:
    return f"P.{external_id.replace('-', '')[:8].upper()}"


def _patient_display_name(row: dict[str, Any]) -> str:
    chosen: str | None = None
    for key in ("display_name", "corpus_short_label", "full_name"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            chosen = val.strip()
            break
    if not chosen:
        name_block = row.get("name")
        if isinstance(name_block, dict):
            first = str(name_block.get("first") or "").strip()
            last = str(name_block.get("last") or "").strip()
            glued = " ".join(part for part in (first, last) if part).strip()
            if glued:
                chosen = glued
    if not chosen:
        external = str(row.get("patient_id", "")).strip()
        chosen = _fallback_patient_label(external) if external else "Unknown synthetic patient"
    assert chosen is not None
    return prettify_synthea_display_name(chosen)


def _patient_metadata(row: dict[str, Any]) -> dict[str, Any]:
    excluded = {"patient_id"}
    return {k: v for k, v in row.items() if k not in excluded}


def _sanitize_patient_metadata_for_display(meta: dict[str, Any]) -> dict[str, Any]:
    """Align JSON metadata with human-facing names used in `patients.name`."""

    out = dict(meta)
    for k in ("display_name", "corpus_short_label", "full_name"):
        val = out.get(k)
        if isinstance(val, str) and val.strip():
            out[k] = prettify_synthea_display_name(val.strip())

    name_block = out.get("name")
    if isinstance(name_block, dict):
        nb: dict[str, Any] = dict(name_block)
        for k in ("first", "middle", "last", "maiden"):
            v = nb.get(k)
            if isinstance(v, str) and v.strip():
                nb[k] = prettify_synthea_token(v.strip())
        out["name"] = nb

    return out


def _entity_payload_from_encounter(enc: dict[str, Any] | None) -> dict[str, Any]:
    if not enc:
        return {}
    payload = enc.get("synthea_encounter")
    if isinstance(payload, dict) and payload:
        spine = dict(payload)
        pname = spine.get("provider_name")
        if isinstance(pname, str) and pname.strip():
            spine["provider_name"] = prettify_synthea_display_name(pname.strip())
        return {"synthea_encounter": spine}
    return {}


def _truncate_ws(s: str, max_chars: int) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    return s[:max_chars] if len(s) > max_chars else s


def _light_md_strip(s: str) -> str:
    """Strip light **bold** wrappers for short UI previews."""

    t = str(s or "").strip()
    t = re.sub(r"\*{2}([^*]+)\*{2}", r"\g<1>", t)
    return t.strip("* \t")


def _heuristic_summary(note_text: str, max_chars: int = 600) -> str:
    """Pick a succinct preview line without matching inner CC inside parentheses."""

    txt = note_text.strip()
    patterns = (
        re.compile(
            r"Chief\s+Complaint(?:\s*\(CC\))?\s*:\**\s*(?:\n\s*)?(?P<head>[^\n]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"Chief\s+Complaint(?:\s*\(CC\))?[\s#\*:]*\s*(?:\n\s*)(?P<head>[^\n#]+)",
            re.IGNORECASE,
        ),
        re.compile(r"\*\*\s*CC\b\s*:\**\s+(?P<head>[^\n]+)", re.IGNORECASE),
        re.compile(
            r"(?m)^(?:\s*\*\*)?CC\b\s*:\**\s+(?P<head>[^\n]+)",
            re.IGNORECASE,
        ),
    )

    for rx in patterns:
        m = rx.search(txt)
        if not m:
            continue
        raw = (m.group("head") or "").strip()
        if not raw or not re.search(r"[A-Za-z]", raw):
            continue
        if re.fullmatch(r"[*\s:.()Cc]+", raw):
            continue
        raw = raw.removeprefix("(CC):").strip()
        lead = _truncate_ws(_light_md_strip(raw), 240)
        if lead:
            return lead

    return _truncate_ws(_light_md_strip(txt[:max_chars]), max_chars)


def _minimal_structured_note(note_text: str) -> dict[str, Any]:
    summary = _heuristic_summary(note_text)
    return {
        "chief_complaint": "",
        "history": "",
        "examination": "",
        "assessment": "",
        "plan": "",
        "follow_up": "",
        "summary": summary,
        "sentiment": "neutral",
        "topics": [],
        "full_note": note_text,
    }


def _parse_session_date(encounter_date: str | None) -> str | None:
    if not encounter_date:
        return None
    try:
        return datetime.fromisoformat(encounter_date.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


def _connect_dsn() -> str:
    load_dotenv(BACKEND_ROOT / ".env")
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit(
            "DATABASE_URL not set (set in backend/.env). "
            "Example: postgresql://rag:rag_dev_password@127.0.0.1:5433/rag_dev"
        )
    return dsn


def load_corpus(*, truncate: bool) -> tuple[int, int]:
    corpus_dir = REPO_ROOT / "data" / "clinical_corpus_v2"
    longitudinal_path = REPO_ROOT / "data" / "staging" / "patient_longitudinal_context.jsonl"
    if not corpus_dir.is_dir():
        raise SystemExit(f"Corpus dir missing: {corpus_dir}")
    if not longitudinal_path.is_file():
        raise SystemExit(f"Longitudinal file missing: {longitudinal_path}")

    patients_rows = _read_jsonl(corpus_dir / "patients.jsonl")
    encounters_rows = _read_jsonl(corpus_dir / "encounters.jsonl")
    notes_rows = _read_jsonl(corpus_dir / "notes.jsonl")
    dialogue_path = corpus_dir / "dialogues.jsonl"
    dialogue_rows = _read_jsonl(dialogue_path) if dialogue_path.is_file() else []

    encounters_by_id = {r["encounter_id"]: r for r in encounters_rows}
    longitudinal_by_encounter = {r["encounter_id"]: r for r in _read_jsonl(longitudinal_path)}
    dialogue_by_encounter = {r["encounter_id"]: r["dialogue_text"] for r in dialogue_rows}

    conn = psycopg2.connect(_connect_dsn())
    conn.autocommit = False

    sql_pat = """
        INSERT INTO patients (domain, external_id, name, metadata)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT ON CONSTRAINT uq_patients_external_id
        DO UPDATE SET
          name = EXCLUDED.name,
          metadata = EXCLUDED.metadata
        RETURNING id, external_id
    """

    patient_id_map: dict[str, str] = {}

    with conn.cursor() as cur:
        if truncate:
            cur.execute("TRUNCATE TABLE notes CASCADE")
            cur.execute("TRUNCATE TABLE patients CASCADE")

        patient_params: list[tuple[Any, ...]] = []
        for pr in patients_rows:
            pid = pr["patient_id"]
            name = _patient_display_name(pr)
            meta = _sanitize_patient_metadata_for_display(_patient_metadata(pr))
            patient_params.append(("clinical", pid, name, Json(meta)))

        for row in tqdm(patient_params, desc="patients"):
            cur.execute(sql_pat, row)
            nid, ext = cur.fetchone()
            patient_id_map[str(ext)] = str(nid)

        orphan_encounters = 0
        note_rows_params: list[tuple[Any, ...]] = []

        for n in notes_rows:
            eid = n["encounter_id"]
            ext_pat = str(n["patient_id"])
            enc = encounters_by_id.get(eid)
            if not enc:
                orphan_encounters += 1
                specialty = None
                sdate = None
            else:
                specialty = enc.get("specialty")
                sdate = _parse_session_date(enc.get("encounter_date"))

            longitudinal = longitudinal_by_encounter.get(eid)
            convo = dialogue_by_encounter.get(eid, "") or ""
            structured = _minimal_structured_note(n.get("note_text") or "")
            corp_note_id = n.get("note_id")
            long_json = Json(longitudinal) if longitudinal is not None else None

            entity_payload = _entity_payload_from_encounter(enc)

            note_rows_params.append(
                (
                    ext_pat,
                    "clinical",
                    eid,
                    corp_note_id,
                    convo,
                    Json(structured),
                    Json(entity_payload),
                    long_json,
                    specialty,
                    "dataset",
                    sdate,
                )
            )

        if orphan_encounters:
            print(f"WARN: {orphan_encounters} notes lacked matching encounter rows (nullable fields).")

        sql_note = """
            INSERT INTO notes (
              patient_id, domain, external_encounter_id, corpus_note_id,
              conversation_text, structured_note, entity_payload, longitudinal_context,
              specialty, source, session_date
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT ON CONSTRAINT uq_notes_external_encounter_id
            DO UPDATE SET
              corpus_note_id = EXCLUDED.corpus_note_id,
              conversation_text = EXCLUDED.conversation_text,
              structured_note = EXCLUDED.structured_note,
              entity_payload = EXCLUDED.entity_payload,
              longitudinal_context = EXCLUDED.longitudinal_context,
              specialty = EXCLUDED.specialty,
              source = EXCLUDED.source,
              session_date = EXCLUDED.session_date,
              patient_id = EXCLUDED.patient_id
        """

        nb: list[tuple[Any, ...]] = []
        for row in note_rows_params:
            ext_pat = row[0]
            if ext_pat not in patient_id_map:
                raise SystemExit(f"No patient UUID for external patient_id={ext_pat}")
            uuid_pat_str = patient_id_map[ext_pat]
            nb.append((uuid_pat_str, *row[1:]))

        execute_batch(cur, sql_note, nb, page_size=100)

    conn.commit()
    conn.close()
    return len(patients_rows), len(note_rows_params)


def _compose_embed_input(structured_note: Any, conversation_text: str | None) -> str:
    sn = structured_note if isinstance(structured_note, dict) else {}
    summary = sn.get("summary") or ""
    full_note = sn.get("full_note") or ""
    conv = (conversation_text or "").strip()
    parts = [str(summary)] if summary else []
    if conv:
        parts.append(conv[:6000])
    parts.append(str(full_note)[:8000])
    out = "\n\n".join(parts)
    out = _truncate_ws(out, 30000)
    return out if out.strip() else "(empty)"


def embed_notes(*, model: str, dimensions: int | None) -> int:
    load_dotenv(BACKEND_ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("SKIP: OPENAI_API_KEY not set — cannot embed.")
        return 0

    conn = psycopg2.connect(_connect_dsn())
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, structured_note, conversation_text
            FROM notes
            WHERE embedding IS NULL
            ORDER BY created_at ASC
            """
        )
        rows = cur.fetchall()
    conn.close()

    client = OpenAI(api_key=api_key)
    batch_size = 32
    updated = 0

    conn = psycopg2.connect(_connect_dsn())
    conn.autocommit = True

    embed_dim_expect = dimensions or int(os.getenv("OPENAI_EMBEDDINGS_DIMENSIONS") or "1536")

    for i in tqdm(range(0, len(rows), batch_size), desc="embedding_batches"):
        chunk = rows[i : i + batch_size]
        inputs = [_compose_embed_input(sn, convo) for _rid, sn, convo in chunk]
        kwargs: dict[str, Any] = {"model": model, "input": inputs}
        if model.startswith("text-embedding-3"):
            kwargs["dimensions"] = embed_dim_expect
        resp = client.embeddings.create(**kwargs)
        ordered = sorted(resp.data, key=lambda d: int(d.index))
        if len(ordered) != len(chunk):
            raise SystemExit("embedding batch length mismatch")

        with conn.cursor() as cur:
            for (rid, _sn, _convo), item in zip(chunk, ordered):
                vec = item.embedding
                if len(vec) != embed_dim_expect:
                    raise SystemExit(
                        f"Embedding dim mismatch: got {len(vec)}, expected {embed_dim_expect}; "
                        "check OPENAI_EMBEDDINGS_DIMENSIONS matches VECTOR(1536)."
                    )
                lit = _vector_literal(vec)
                cur.execute(
                    "UPDATE notes SET embedding = %s::vector WHERE id = %s::uuid",
                    (lit, str(rid)),
                )
                updated += 1

    conn.close()
    print(f"Embedded {updated} notes (dimensions={embed_dim_expect}).")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Scribe-IQ corpus JSONL into Postgres.")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE patients/notes before load (destructive reset).",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Backfill embeddings where notes.embedding IS NULL (requires OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--embed-model",
        default=os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small"),
    )
    parser.add_argument(
        "--embed-dim",
        type=int,
        default=int(os.getenv("OPENAI_EMBEDDINGS_DIMENSIONS") or "1536"),
    )
    args = parser.parse_args()

    npat, nnote = load_corpus(truncate=args.truncate)
    print(f"Loaded patients={npat} notes={nnote}")

    if args.embed:
        embed_notes(model=args.embed_model, dimensions=args.embed_dim)


if __name__ == "__main__":
    main()
