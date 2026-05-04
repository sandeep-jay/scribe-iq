from __future__ import annotations


def score_match(encounter: dict, note: dict) -> float:
    score = 0.0

    if note["specialty"] == encounter["specialty"]:
        score += 0.40
    elif note["specialty"] == "General Medicine":
        score += 0.08

    note_icd = note.get("icd10_code") or ""
    enc_icd_list = encounter.get("icd10_codes", [])
    if note_icd and enc_icd_list:
        for enc_icd in enc_icd_list:
            if not enc_icd:
                continue
            if note_icd[:3] == enc_icd[:3]:
                score += 0.35
                break
            elif note_icd[0] == enc_icd[0]:
                score += 0.12
                break

    conditions = encounter.get("conditions", [])
    note_text = (note.get("note_text") or "").lower()
    if conditions:
        matched = sum(
            1
            for cond in conditions
            if any(
                word in note_text
                for word in cond.lower().split()
                if len(word) >= 5
            )
        )
        score += 0.15 * (matched / len(conditions))

    tier_weights = {"primary": 0.05, "secondary": 0.02, "fallback": 0.0}
    score += tier_weights.get(note.get("quality_tier", "fallback"), 0)

    if note.get("dialogue"):
        score += 0.05

    return round(min(score, 1.0), 3)
