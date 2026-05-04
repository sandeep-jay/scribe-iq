"""
06_adapt_notes.py — run from data_prep/
"""
from __future__ import annotations


import sys
from pathlib import Path as _Path

_DP_ROOT = _Path(__file__).resolve().parent.parent
if str(_DP_ROOT) not in sys.path:
    sys.path.insert(0, str(_DP_ROOT))


import os
import time
from collections import defaultdict
from pathlib import Path

from groq import Groq

from utils.io_utils import count_jsonl, load_jsonl, write_jsonl
from utils.note_checks import check_note_coherence
from utils.synthea_utils import compute_age, load_synthea

REPO_ROOT = Path(__file__).resolve().parents[2]


def _selected_patients_jsonl() -> Path:
    override = os.environ.get("SCRIBE_SELECTED_PATIENTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    golden = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
    if golden.is_file():
        return golden
    return REPO_ROOT / "data/staging/selected_patients.jsonl"

def _match_results_jsonl() -> Path:
    override = os.environ.get("SCRIBE_MATCH_RESULTS_JSONL", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else REPO_ROOT / p
    golden = REPO_ROOT / "data/staging/match_results_golden.jsonl"
    if golden.is_file():
        return golden
    return REPO_ROOT / "data/staging/match_results.jsonl"

def _longitudinal_context_path() -> Path:
    override = os.environ.get("SCRIBE_LONGITUDINAL_CONTEXT_JSONL", "").strip()
    if not override:
        return REPO_ROOT / "data/staging/patient_longitudinal_context.jsonl"
    p = Path(override)
    return p if p.is_absolute() else REPO_ROOT / p


ACI_RES = REPO_ROOT / "data/staging/aci_reservations.jsonl"
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
OUTPUT = REPO_ROOT / "data/staging/adapted_notes.jsonl"

MODEL = os.environ.get(
    "GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)


def _adapt_resume_enabled() -> bool:
    v = os.environ.get("SCRIBE_ADAPT_RESUME", "").strip().lower()
    return v in ("1", "true", "yes")


def _load_resume_state(path: Path) -> tuple[set[tuple[str, str]], int, set[str]]:
    """Return (done patient_id+encounter_id, next note index, ACI note_ids already used)."""
    done: set[tuple[str, str]] = set()
    aci_ids: set[str] = set()
    next_idx = 0
    if not path.exists():
        return done, next_idx, aci_ids
    for r in load_jsonl(path):
        pid = r["patient_id"]
        eid = r["encounter_id"]
        done.add((pid, eid))
        aid = r.get("adapted_note_id") or ""
        if aid.startswith("note_"):
            try:
                next_idx = max(next_idx, int(aid[5:], 10) + 1)
            except ValueError:
                pass
        if (
            r.get("is_showcase")
            and r.get("reference_source") == "aci_bench"
            and r.get("reference_note_id")
        ):
            aci_ids.add(str(r["reference_note_id"]))
    return done, next_idx, aci_ids

ADAPT_PROMPT = """\
You are a clinical documentation specialist.
Adapt the REFERENCE NOTE to match the PATIENT DATA below.

Rules:
1. Keep the EXACT same section format and structure as the reference note
2. Keep the clinical writing style, tone, and approximate length
3. Replace any conditions or medications that CONFLICT with the patient data
4. Do NOT add conditions or medications not present in the patient data
5. Do NOT invent lab values — only use values provided below
6. Do NOT include any patient name or identifying information
7. Output only the adapted note text — no preamble, no explanation
8. Use PRIOR VISITS only for continuity; if they conflict with this visit, prefer PATIENT DATA below

PRIOR VISITS (structured chart memory):
{prior_visits_section}

PATIENT DATA:
- Age: {age}
- Sex: {sex}
- Visit date: {visit_date}
- Visit reason: {visit_reason}
- Active conditions: {conditions}
- Current medications: {medications}
- Recent labs/vitals: {observations}

REFERENCE NOTE:
{reference_note}"""


def call_groq(client: Groq, prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=900,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1}: {e}")
                time.sleep(2 ** attempt)
            else:
                raise


def format_obs(obs_list: list) -> str:
    if not obs_list:
        return "None recorded"
    lines = []
    for o in obs_list[:8]:
        lines.append(
            f"- {o.get('DESCRIPTION','')}: {o.get('VALUE','')} {o.get('UNITS','')}".strip()
        )
    return "\n".join(lines)


def format_prior_context(blocks: list) -> str:
    if not blocks:
        return "No prior visits in window."
    lines_out: list[str] = []
    for i, b in enumerate(blocks, 1):
        eid = b.get("encounter_id", "")
        lines_out.append(f"Prior {i} ({b.get('date', '')}) [encounter {eid}]:")
        lines_out.append(f"  Reason: {b.get('reason', '')}")
        conds = b.get("conditions") or []
        if conds:
            lines_out.append(f"  Conditions: {', '.join(str(c) for c in conds)}")
        meds = b.get("medications") or []
        if meds:
            lines_out.append(f"  Medications: {', '.join(str(m) for m in meds)}")
        ko = b.get("key_observations") or []
        if ko:
            lines_out.append(f"  Key observations: {'; '.join(str(x) for x in ko)}")
    return "\n".join(lines_out)


def prior_visits_section(
    context_lookup: dict[tuple[str, str], dict], pid: str, enc_id: str
) -> str:
    row = context_lookup.get((pid, enc_id))
    if not row:
        return (
            "No structured prior window loaded for this encounter "
            "(optional: run 05.5_extract_longitudinal_context.py)."
        )
    return format_prior_context(row.get("prior_visits") or [])


def main() -> None:
    _ = os.environ["GROQ_API_KEY"]
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    synthea = load_synthea(SYNTHEA_DIR)
    patients_df = synthea["patients"]

    selected_path = _selected_patients_jsonl()
    matches_path = _match_results_jsonl()
    ctx_path = _longitudinal_context_path()
    context_lookup: dict[tuple[str, str], dict] = {}
    if ctx_path.exists():
        for r in load_jsonl(ctx_path):
            context_lookup[(r["patient_id"], r["encounter_id"])] = r
        print(f"Longitudinal context: {len(context_lookup)} rows from {ctx_path.name}")
    else:
        print(f"Longitudinal context: none ({ctx_path.name} missing — prompts omit prior window file)")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    resume = _adapt_resume_enabled()
    if resume:
        done_keys, note_idx, aci_resume = _load_resume_state(OUTPUT)
        if done_keys:
            print(
                f"Resume: keeping {count_jsonl(OUTPUT)} lines; "
                f"skipping {len(done_keys)} patient+encounter pair(s) already in {OUTPUT.name}"
            )
    else:
        OUTPUT.unlink(missing_ok=True)
        done_keys = set()
        note_idx = 0
        aci_resume = set()

    aci_by_specialty: dict[str, list] = defaultdict(list)
    if ACI_RES.exists():
        for r in load_jsonl(ACI_RES):
            aci_by_specialty[r["specialty"]].append(r)
    aci_used: set[str] = set(aci_resume)

    by_patient: dict[str, list] = defaultdict(list)
    for m in load_jsonl(matches_path):
        by_patient[m["patient_id"]].append(m)

    selected = list(load_jsonl(selected_path))

    for patient in selected:
        pid = patient["patient_id"]
        pt = patients_df[patients_df["Id"] == pid].iloc[0]
        sex = "Male" if pt["GENDER"] == "M" else "Female"
        spec = patient["primary_specialty"]

        pt_matches = sorted(
            by_patient[pid], key=lambda x: (x["encounter_date"], x["encounter_id"])
        )
        prior_visits = pt_matches[:-1]
        current_visit = pt_matches[-1]

        print(f"\n{pid}  {spec}  {len(pt_matches)} encounters")

        for enc in prior_visits:
            if not enc.get("best_note_text"):
                continue
            if (pid, enc["encounter_id"]) in done_keys:
                continue
            age = compute_age(pt["BIRTHDATE"], enc["encounter_date"])
            prompt = ADAPT_PROMPT.format(
                prior_visits_section=prior_visits_section(
                    context_lookup, pid, enc["encounter_id"]
                ),
                age=age,
                sex=sex,
                visit_date=enc["encounter_date"][:10],
                visit_reason=enc.get("encounter_reason", "Follow-up visit"),
                conditions=", ".join(enc.get("conditions", [])) or "None documented",
                medications=", ".join(enc.get("medications", [])) or "None documented",
                observations=format_obs(enc.get("recent_obs", [])),
                reference_note=enc["best_note_text"][:2500],
            )
            print(
                f"  [{enc['encounter_date'][:10]}] adapting "
                f"({enc['best_note_source']}, score={enc['match_score']:.2f})...",
                end=" ",
                flush=True,
            )
            adapted = call_groq(client, prompt)
            issues = check_note_coherence(
                adapted,
                enc.get("conditions", []),
                enc.get("medications", []),
            )
            if issues:
                print(f"⚠ {len(issues)} coherence warning(s): {issues[:2]}")
            else:
                print("ok")
            rec_out = {
                    "adapted_note_id": f"note_{note_idx:06d}",
                    "encounter_id": enc["encounter_id"],
                    "patient_id": pid,
                    "encounter_date": enc["encounter_date"],
                    "note_text": adapted,
                    "reference_note_id": enc["best_note_id"],
                    "reference_source": enc["best_note_source"],
                    "match_score": enc["match_score"],
                    "coherence_issues": issues,
                    "is_showcase": False,
                    "has_dialogue": False,
                }
            _ctx = context_lookup.get((pid, enc["encounter_id"]))
            if _ctx is not None:
                rec_out["num_prior_visits_in_context"] = _ctx.get("num_prior_visits", 0)
            write_jsonl(OUTPUT, rec_out)
            note_idx += 1

        aci_candidates = [
            r for r in aci_by_specialty.get(spec, []) if r["note_id"] not in aci_used
        ]
        if not aci_candidates:
            aci_candidates = [
                r
                for r in aci_by_specialty.get("General Medicine", [])
                if r["note_id"] not in aci_used
            ]

        if (pid, current_visit["encounter_id"]) not in done_keys:
            if aci_candidates:
                gender_match = [
                    c
                    for c in aci_candidates
                    if str(c.get("gender", "")).upper() == str(pt["GENDER"]).upper()
                ]
                aci_enc = gender_match[0] if gender_match else aci_candidates[0]
                aci_used.add(aci_enc["note_id"])
                rec_aci = {
                        "adapted_note_id": f"note_{note_idx:06d}",
                        "encounter_id": current_visit["encounter_id"],
                        "patient_id": pid,
                        "encounter_date": current_visit["encounter_date"],
                        "note_text": aci_enc["note_text"],
                        "dialogue": aci_enc["dialogue"],
                        "reference_note_id": aci_enc["note_id"],
                        "reference_source": "aci_bench",
                        "match_score": current_visit["match_score"],
                        "coherence_issues": [],
                        "is_showcase": True,
                        "has_dialogue": True,
                    }
                _ctxa = context_lookup.get((pid, current_visit["encounter_id"]))
                if _ctxa is not None:
                    rec_aci["num_prior_visits_in_context"] = _ctxa.get("num_prior_visits", 0)
                write_jsonl(OUTPUT, rec_aci)
                print(
                    f"  [{current_visit['encounter_date'][:10]}] showcase → ACI-Bench "
                    f"({aci_enc['specialty']}, {aci_enc.get('gender','')})"
                )
                note_idx += 1
            else:
                if current_visit.get("best_note_text"):
                    age = compute_age(pt["BIRTHDATE"], current_visit["encounter_date"])
                    prompt = ADAPT_PROMPT.format(
                        prior_visits_section=prior_visits_section(
                            context_lookup, pid, current_visit["encounter_id"]
                        ),
                        age=age,
                        sex=sex,
                        visit_date=current_visit["encounter_date"][:10],
                        visit_reason=current_visit.get("encounter_reason", "Follow-up"),
                        conditions=", ".join(current_visit.get("conditions", [])) or "None",
                        medications=", ".join(current_visit.get("medications", [])) or "None",
                        observations=format_obs(current_visit.get("recent_obs", [])),
                        reference_note=current_visit["best_note_text"][:2500],
                    )
                    adapted = call_groq(client, prompt)
                    dialogue = current_visit.get("best_note_dialogue")
                    rec_show = {
                            "adapted_note_id": f"note_{note_idx:06d}",
                            "encounter_id": current_visit["encounter_id"],
                            "patient_id": pid,
                            "encounter_date": current_visit["encounter_date"],
                            "note_text": adapted,
                            "dialogue": dialogue,
                            "reference_source": current_visit["best_note_source"],
                            "match_score": current_visit["match_score"],
                            "coherence_issues": [],
                            "is_showcase": True,
                            "has_dialogue": bool(dialogue),
                        }
                    _ctxs = context_lookup.get((pid, current_visit["encounter_id"]))
                    if _ctxs is not None:
                        rec_show["num_prior_visits_in_context"] = _ctxs.get(
                            "num_prior_visits", 0
                        )
                    write_jsonl(OUTPUT, rec_show)
                    print(
                        f"  [{current_visit['encounter_date'][:10]}] showcase → adapted "
                        f"(no ACI available, dialogue={'yes' if dialogue else 'no'})"
                    )
                    note_idx += 1

    print(f"\n✓ Adaptation complete: {count_jsonl(OUTPUT)} lines → {OUTPUT}")


if __name__ == "__main__":
    main()
