"""Map Synthea CSV rows to demo JSON (omit government-style IDs)."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from utils.synthea_name_prettify import prettify_synthea_display_name, prettify_synthea_token


def scalar(v: Any) -> Any | None:
    if v is None:
        return None
    if hasattr(v, "item") and callable(v.item) and type(v).__name__ != "Timestamp":
        try:
            inner = v.item()
        except Exception:
            inner = None
        if inner is v:
            return v
        return scalar(inner)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def _str_scalar(pt: pd.Series, key: str) -> str:
    v = scalar(pt.get(key))
    return str(v).strip() if v is not None and str(v).strip() else ""


def patient_demo_fields(pt: pd.Series) -> dict[str, Any]:
    prefix = _str_scalar(pt, "PREFIX")
    first = _str_scalar(pt, "FIRST")
    middle = _str_scalar(pt, "MIDDLE")
    last = _str_scalar(pt, "LAST")
    suffix = _str_scalar(pt, "SUFFIX")
    maiden = _str_scalar(pt, "MAIDEN")

    pieces = [p for p in (prefix, first, middle, last, suffix) if p]
    display = prettify_synthea_display_name(" ".join(pieces).strip())
    pretty_maiden = (prettify_synthea_display_name(maiden.strip()) if maiden else "")
    if pretty_maiden and display:
        display = f"{display} (née {pretty_maiden})"
    elif pretty_maiden and not display:
        display = f"(née {pretty_maiden})"

    birth_iso = None
    death_iso = None
    birth_year = None

    birth_raw = scalar(pt.get("BIRTHDATE"))
    birth_dt = pd.to_datetime(pt.get("BIRTHDATE"), utc=False, errors="coerce")
    if pd.notna(birth_dt):
        birth_iso = str(birth_dt.date().isoformat())
        birth_year = int(birth_dt.year)
    elif birth_raw not in (None, ""):
        birth_iso = str(birth_raw)[:10]

    death_dt = pd.to_datetime(pt.get("DEATHDATE"), utc=False, errors="coerce")
    if pd.notna(death_dt):
        death_iso = str(death_dt.date().isoformat())

    lat = scalar(pt.get("LAT"))
    lon = scalar(pt.get("LON"))

    return {
        "display_name": display,
        "name": {
            "prefix": prefix or None,
            "first": (prettify_synthea_token(first) if first else None),
            "middle": (prettify_synthea_token(middle) if middle else None),
            "last": (prettify_synthea_token(last) if last else None),
            "suffix": suffix or None,
            "maiden": (prettify_synthea_token(maiden) if maiden else None),
        },
        "birthdate": birth_iso,
        "birth_year": birth_year,
        "deathdate": death_iso,
        "sex": (_str_scalar(pt, "GENDER") or None),
        "marital_status": (_str_scalar(pt, "MARITAL") or None),
        "race": (_str_scalar(pt, "RACE") or None),
        "ethnicity": (_str_scalar(pt, "ETHNICITY") or None),
        "birthplace": (_str_scalar(pt, "BIRTHPLACE") or None),
        "address": {
            "line": (_str_scalar(pt, "ADDRESS") or None),
            "city": (_str_scalar(pt, "CITY") or None),
            "state": (_str_scalar(pt, "STATE") or None),
            "county": (_str_scalar(pt, "COUNTY") or None),
            "fips": (_str_scalar(pt, "FIPS") or None),
            "zip": (_str_scalar(pt, "ZIP") or None),
            "latitude": lat,
            "longitude": lon,
        },
        "economics": {
            "healthcare_expenses": scalar(pt.get("HEALTHCARE_EXPENSES")),
            "healthcare_coverage": scalar(pt.get("HEALTHCARE_COVERAGE")),
            "annual_income": scalar(pt.get("INCOME")),
        },
    }


def _series_field(row: pd.Series | None, column: str) -> Any:
    if row is None:
        return None
    return scalar(row.get(column))


def _row_by_id(frame: pd.DataFrame | None, raw_id: Any) -> pd.Series | None:
    pk = scalar(raw_id)
    if pk is None or frame is None or frame.empty:
        return None
    if "Id" not in frame.columns:
        return None
    hits = frame[frame["Id"].astype(str) == str(pk)]
    return None if hits.empty else hits.iloc[0]


def encounter_demo_fields(
    er: pd.Series,
    *,
    organizations: pd.DataFrame | None = None,
    providers: pd.DataFrame | None = None,
    payers: pd.DataFrame | None = None,
) -> dict[str, Any]:
    start_dt = pd.to_datetime(er.get("START"), utc=False, errors="coerce")
    stop_dt = pd.to_datetime(er.get("STOP"), utc=False, errors="coerce")

    org_id = scalar(er.get("ORGANIZATION"))
    prov_id = scalar(er.get("PROVIDER"))
    pay_id = scalar(er.get("PAYER"))

    org_row = _row_by_id(organizations, org_id)
    prov_row = _row_by_id(providers, prov_id)
    pay_row = _row_by_id(payers, pay_id)

    org_city = _series_field(org_row, "CITY")
    org_state = _series_field(org_row, "STATE")
    org_zip = _series_field(org_row, "ZIP")
    org_phone = _series_field(org_row, "PHONE")

    org_location_parts = []
    for chunk in (
        str(org_city).strip() if isinstance(org_city, str) else org_city,
        str(org_state).strip() if isinstance(org_state, str) else org_state,
    ):
        if isinstance(chunk, str) and chunk:
            org_location_parts.append(chunk)
    org_location = ", ".join(org_location_parts) if org_location_parts else None

    pname_raw = _series_field(prov_row, "NAME")
    if isinstance(pname_raw, str) and pname_raw.strip():
        pname_pf = prettify_synthea_display_name(pname_raw.strip())
    else:
        pname_pf = pname_raw

    return {
        "start": start_dt.isoformat() if pd.notna(start_dt) else None,
        "stop": stop_dt.isoformat() if pd.notna(stop_dt) else None,
        # Encounter FKs — kept for downstream joins / reproducibility.
        "organization": org_id,
        "organization_name": _series_field(org_row, "NAME"),
        "organization_city": org_city,
        "organization_state": org_state,
        "organization_zip": org_zip,
        "organization_phone": org_phone,
        "organization_location": org_location,
        "organization_address_line": _series_field(org_row, "ADDRESS"),
        "provider": prov_id,
        "provider_name": pname_pf,
        "provider_specialty": _series_field(prov_row, "SPECIALITY")
        or _series_field(prov_row, "SPECIALTY"),
        "provider_gender": _series_field(prov_row, "GENDER"),
        "payer": pay_id,
        "payer_name": _series_field(pay_row, "NAME"),
        "payer_ownership": _series_field(pay_row, "OWNERSHIP"),
        "encounter_class": scalar(er.get("ENCOUNTERCLASS")),
        "encounter_code": scalar(er.get("CODE")),
        "encounter_description": scalar(er.get("DESCRIPTION")),
        "base_encounter_cost": scalar(er.get("BASE_ENCOUNTER_COST")),
        "total_claim_cost": scalar(er.get("TOTAL_CLAIM_COST")),
        "payer_coverage": scalar(er.get("PAYER_COVERAGE")),
        "reason_code": scalar(er.get("REASONCODE")),
        "reason_description": scalar(er.get("REASONDESCRIPTION")),
    }


def patient_row_for_corpus(pid: str, pt: pd.Series, selection_meta: dict[str, Any]) -> dict[str, Any]:
    spine = patient_demo_fields(pt)
    merged: dict[str, Any] = {
        "patient_id": pid,
        "primary_specialty": selection_meta.get("primary_specialty"),
        "encounter_count": selection_meta.get("encounter_count"),
        "quality_score": selection_meta.get("quality_score"),
        "synthetic_source": "synthea_v3",
    }
    merged.update(spine)

    merged.setdefault("race", spine.get("race") or "")
    merged.setdefault("ethnicity", spine.get("ethnicity") or "")
    merged.setdefault("sex", spine.get("sex") or "")

    short = (merged.get("display_name") or "").strip()
    if short:
        merged["corpus_short_label"] = short
    return merged
