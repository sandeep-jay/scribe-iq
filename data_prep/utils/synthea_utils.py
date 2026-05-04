
from __future__ import annotations

from pathlib import Path

import pandas as pd

_CONDITIONS_COLS = ["START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION"]
_MEDS_COLS = [
    "START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION",
    "BASE_COST", "PAYER_COVERAGE", "DISPENSES", "TOTALCOST", "REASONDESCRIPTION",
]
_OBS_COLS = ["DATE", "PATIENT", "ENCOUNTER", "CATEGORY", "CODE", "DESCRIPTION", "VALUE", "UNITS", "TYPE"]


def _utc_naive(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, utc=True)
    if getattr(dt.dt, "tz", None) is not None:
        return dt.dt.tz_localize(None)
    return dt


def load_synthea(csv_dir: Path) -> dict:
    """Load Synthea CSV output from *csv_dir*.

    Core clinical spine: ``patients``, ``encounters``, ``conditions``, ``medications``, ``observations``.

    Demo joins (optional CSVs resolved by ``Id`` when present):

    ``organizations``, ``providers``, ``payers`` for encounter-side lookup labels.
    Missing optional tables become empty DataFrames.
    """
    csv_dir = Path(csv_dir)

    def _read(name: str, empty_cols: list[str]) -> pd.DataFrame:
        path = csv_dir / name
        if not path.exists():
            return pd.DataFrame(columns=empty_cols)
        return pd.read_csv(path)

    patients = pd.read_csv(csv_dir / "patients.csv")
    encounters = pd.read_csv(csv_dir / "encounters.csv")

    def _maybe_read(csv_name: str) -> pd.DataFrame:
        path = csv_dir / csv_name
        return pd.DataFrame() if not path.exists() else pd.read_csv(path)

    organizations = _maybe_read("organizations.csv")
    providers = _maybe_read("providers.csv")
    payers = _maybe_read("payers.csv")

    conditions = _read("conditions.csv", _CONDITIONS_COLS)
    medications = _read("medications.csv", _MEDS_COLS)
    observations = _read("observations.csv", _OBS_COLS)

    if not encounters.empty:
        for col in ("START", "STOP"):
            if col in encounters.columns:
                encounters[col] = _utc_naive(encounters[col])
    if not conditions.empty:
        for col in ("START", "STOP"):
            if col in conditions.columns:
                conditions[col] = _utc_naive(conditions[col])
    if not medications.empty:
        for col in ("START", "STOP"):
            if col in medications.columns:
                medications[col] = _utc_naive(medications[col])
    if not observations.empty and "DATE" in observations.columns:
        observations["DATE"] = _utc_naive(observations["DATE"])

    if "BIRTHDATE" in patients.columns:
        patients["BIRTHDATE"] = _utc_naive(patients["BIRTHDATE"])

    return {
        "patients": patients,
        "encounters": encounters,
        "organizations": organizations,
        "providers": providers,
        "payers": payers,
        "conditions": conditions,
        "medications": medications,
        "observations": observations,
    }


def get_active_conditions(df, patient_id, as_of_date):
    if df.empty:
        return df
    as_of = pd.to_datetime(as_of_date)
    if getattr(as_of, "tzinfo", None) is not None:
        as_of = as_of.tz_convert("UTC").tz_localize(None)
    mask = (
        (df["PATIENT"] == patient_id)
        & (pd.to_datetime(df["START"]) <= as_of)
        & (df["STOP"].isna() | (pd.to_datetime(df["STOP"]) >= as_of))
    )
    return df[mask]


def get_active_medications(df, patient_id, as_of_date):
    if df.empty:
        return df
    as_of = pd.to_datetime(as_of_date)
    if getattr(as_of, "tzinfo", None) is not None:
        as_of = as_of.tz_convert("UTC").tz_localize(None)
    mask = (
        (df["PATIENT"] == patient_id)
        & (pd.to_datetime(df["START"]) <= as_of)
        & (df["STOP"].isna() | (pd.to_datetime(df["STOP"]) >= as_of))
    )
    return df[mask]


def compute_age(birth_date_str: str, as_of_date_str: str) -> int:
    birth = pd.to_datetime(birth_date_str)
    if getattr(birth, "tzinfo", None) is not None:
        birth = birth.tz_convert("UTC").tz_localize(None)
    as_of = pd.to_datetime(as_of_date_str)
    if getattr(as_of, "tzinfo", None) is not None:
        as_of = as_of.tz_convert("UTC").tz_localize(None)
    return int((as_of - birth).days / 365.25)
