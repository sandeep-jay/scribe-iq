from __future__ import annotations

import re

_COMMON_DRUG_SUFFIXES = (
    "olol", "pril", "sartan", "statin", "mycin",
    "cillin", "azole", "prazole", "tidine", "dipine",
)


def check_note_coherence(
    note_text: str,
    expected_conditions: list,
    expected_medications: list,
) -> list:
    """Heuristics: length + possible medications not in allowlist.

    expected_conditions is accepted for API compatibility; not used yet.
    """
    del expected_conditions
    issues: list[str] = []
    note_lower = note_text.lower()

    wc = len(note_text.split())
    if wc < 50:
        issues.append(
            f"Note is very short ({wc} words) — possible adaptation failure"
        )

    allowed_med_tokens: set[str] = set()
    for med in expected_medications:
        for token in med.lower().split():
            if len(token) >= 5:
                allowed_med_tokens.add(token)

    for suffix in _COMMON_DRUG_SUFFIXES:
        pattern = rf"\b\w+{re.escape(suffix)}\b"
        for match in re.findall(pattern, note_lower):
            if match not in allowed_med_tokens and len(match) >= 7:
                issues.append(f"Possible unlisted medication in note: '{match}'")
                break

    return issues
