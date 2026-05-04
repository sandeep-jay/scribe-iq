# Scribe-IQ — Data Generation Pipeline
## Full Cursor Prompt

---

## Project Context

Build the data generation pipeline for **Scribe-IQ**, an intelligent clinical interface
featuring pre-meeting patient summaries, note generation, and transcription.

The pipeline produces a synthetic clinical corpus of 50 carefully selected patients,
each with coherent longitudinal health records, prior visit notes, and a showcase
encounter dialogue.

**Stack:** Python 3.11, pandas, datasets (HuggingFace), groq, pathlib
**Machine:** M1 Max, 32GB RAM, macOS
**Cost:** $0 — all free tier APIs and open datasets

---

## Repository Structure to Create

```
scribe-iq/
  data_prep/
    scripts/
      01_generate_patients.sh
      02_build_note_pool.py
      03_match_and_score.py
      04_select_patients.py
      05_adapt_notes.py
      06_assemble_corpus.py
      07_validate_corpus.py
    utils/
      __init__.py
      mappings.py          ← SNOMED→ICD10, ICD10→Specialty lookups
      io_utils.py          ← read/write jsonl helpers
      synthea_utils.py     ← load and parse Synthea CSV outputs
      scoring.py           ← match scoring logic
    requirements.txt
    README.md
  data/
    raw/
      synthea/             ← Synthea CSV output goes here
      aci_bench/           ← ACI-Bench CSVs go here
    staging/
      note_pool.jsonl      ← built by script 02
      match_results.jsonl  ← built by script 03
      selected_patients.jsonl ← built by script 04
    clinical_corpus/
      patients.jsonl
      encounters.jsonl
      notes.jsonl
      conditions.jsonl
      medications.jsonl
      observations.jsonl
      dialogues.jsonl
      source_provenance.jsonl
      manifest.json
      audit_report.md
      dataset_card.md
  roadmap/
    CLINICAL_LAKEHOUSE_PROPOSAL_V2.md
```

---

## Script 01 — Generate Patients

**File:** `data_prep/scripts/01_generate_patients.sh`

```bash
#!/bin/bash
# Generates 1000 synthetic patients using Synthea
# Requires: Java 11+, synthea-with-dependencies.jar in project root
# Download from: https://github.com/synthetichealth/synthea/releases

set -e

OUTPUT_DIR="data/raw/synthea"
mkdir -p "$OUTPUT_DIR"

java -jar synthea-with-dependencies.jar \
  -p 1000 \
  -s 42 \
  --exporter.csv.export true \
  --exporter.fhir.export false \
  --exporter.baseDirectory "$OUTPUT_DIR" \
  -m "heart_disease,hypertension,diabetes,stroke,epilepsy,\
colorectal_cancer,crohns_disease,osteoporosis,\
osteoarthritis,asthma,copd,kidney_disease,\
dermatitis,hypothyroidism,anxiety,depression,\
lung_cancer,atrial_fibrillation,alzheimers,\
rheumatoid_arthritis,macular_degeneration"

echo "Synthea generation complete."
echo "Output: $OUTPUT_DIR/csv/"
ls -lh "$OUTPUT_DIR/csv/"
```

---

## Script 02 — Build Note Pool

**File:** `data_prep/scripts/02_build_note_pool.py`

Build a unified, indexed pool of clinical notes from three sources:
- **MedSynth** — 10k SOAP dialogue-note pairs, ICD-10 coded (HuggingFace: `Ahmad0067/MedSynth`)
- **MTSamples** — 5k medical transcriptions, specialty-labeled (HuggingFace: `harishnair04/mtsamples`)
- **ACI-Bench** — 207 full encounter dialogues, expert-created (GitHub: `microsoft/clinical_visit_note_summarization_corpus`)

### Requirements

```
datasets>=2.14.0
pandas>=2.0.0
tqdm
```

### Implementation

```python
"""
02_build_note_pool.py

Builds a unified note pool from MedSynth, MTSamples, and ACI-Bench.
Output: data/staging/note_pool.jsonl

Each record:
{
    "note_id": str,
    "source": "medsynth" | "mtsamples" | "aci_bench",
    "specialty": str,
    "icd10_code": str | null,
    "icd10_desc": str | null,
    "note_type": "soap" | "progress_note" | "full_encounter",
    "note_text": str,
    "dialogue": str | null,
    "chief_complaint": str | null,
    "gender": str | null,
    "word_count": int,
    "quality_tier": "primary" | "secondary" | "fallback"
}
"""

from pathlib import Path
from datasets import load_dataset
import pandas as pd
import json
from tqdm import tqdm
from utils.mappings import ICD10_TO_SPECIALTY, MTSAMPLES_TO_STANDARD_SPECIALTY
from utils.io_utils import write_jsonl, count_jsonl

OUTPUT = Path("data/staging/note_pool.jsonl")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.unlink(missing_ok=True)  # start fresh

# ─── MTSamples outpatient filter ──────────────────────────────────────────────
OUTPATIENT_KEYWORDS = [
    "progress note", "office visit", "office note", "soap",
    "follow-up", "followup", "follow up", "clinic note",
    "consult", "history and physical", "h&p", "outpatient",
    "checkup", "check-up", "annual", "wellness", "recheck"
]

EXCLUDED_SPECIALTIES = [
    "Surgery", "Neurosurgery", "Radiology", "Lab Medicine - Pathology",
    "Letters", "Discharge Summary", "Emergency Room Reports",
    "Autopsy", "IME-QME-Work Comp etc.", "Cosmetic / Plastic Surgery"
]

def is_outpatient_note(row) -> bool:
    if row.get("medical_specialty", "") in EXCLUDED_SPECIALTIES:
        return False
    text = f"{row.get('sample_name','')} {row.get('description','')}".lower()
    return any(kw in text for kw in OUTPATIENT_KEYWORDS)


# ─── Load MedSynth ────────────────────────────────────────────────────────────
print("\n[1/3] Loading MedSynth...")
medsynth = load_dataset("Ahmad0067/MedSynth", split="train")

for idx, row in enumerate(tqdm(medsynth)):
    icd10 = row.get("ICD10", "")
    specialty = ICD10_TO_SPECIALTY.get(icd10[0] if icd10 else "X", "General Medicine")

    record = {
        "note_id": f"ms_{idx:06d}",
        "source": "medsynth",
        "specialty": specialty,
        "icd10_code": icd10,
        "icd10_desc": row.get("ICD10_desc", ""),
        "note_type": "soap",
        "note_text": row.get("note", ""),
        "dialogue": row.get("dialogue", ""),
        "chief_complaint": None,
        "gender": None,
        "word_count": len(row.get("note", "").split()),
        "quality_tier": "primary",
    }
    write_jsonl(OUTPUT, record)

print(f"  MedSynth: {count_jsonl(OUTPUT)} records so far")


# ─── Load MTSamples ───────────────────────────────────────────────────────────
print("\n[2/3] Loading MTSamples...")
mtsamples = load_dataset("harishnair04/mtsamples", split="train")

mts_count = 0
for idx, row in enumerate(tqdm(mtsamples)):
    if not is_outpatient_note(row):
        continue
    if not row.get("transcription") or len(row["transcription"]) < 100:
        continue

    raw_specialty = row.get("medical_specialty", "General Medicine").strip()
    specialty = MTSAMPLES_TO_STANDARD_SPECIALTY.get(raw_specialty, raw_specialty)

    record = {
        "note_id": f"mts_{idx:06d}",
        "source": "mtsamples",
        "specialty": specialty,
        "icd10_code": None,
        "icd10_desc": None,
        "note_type": "progress_note",
        "note_text": row["transcription"],
        "dialogue": None,
        "chief_complaint": row.get("description", ""),
        "gender": None,
        "keywords": row.get("keywords", ""),
        "word_count": len(row["transcription"].split()),
        "quality_tier": "primary",  # human-written
    }
    write_jsonl(OUTPUT, record)
    mts_count += 1

print(f"  MTSamples: {mts_count} outpatient notes added")


# ─── Load ACI-Bench ───────────────────────────────────────────────────────────
print("\n[3/3] Loading ACI-Bench...")
# Clone https://github.com/microsoft/clinical_visit_note_summarization_corpus
# to data/raw/aci_bench/
aci_dir = Path("data/raw/aci_bench")

if not aci_dir.exists():
    print("  WARNING: ACI-Bench not found at data/raw/aci_bench/")
    print("  Clone: github.com/microsoft/clinical_visit_note_summarization_corpus")
    print("  Skipping ACI-Bench for now.")
else:
    aci_count = 0
    for meta_file in aci_dir.glob("*metadata*.csv"):
        meta_df = pd.read_csv(meta_file)
        # Find matching source-target file
        src_tgt_file = meta_file.parent / meta_file.name.replace("metadata", "src-tgt")
        if not src_tgt_file.exists():
            continue
        src_tgt_df = pd.read_csv(src_tgt_file)
        merged = meta_df.merge(src_tgt_df, on=["id", "encounter_id"], how="inner")

        for _, row in merged.iterrows():
            record = {
                "note_id": f"aci_{row['encounter_id']}",
                "source": "aci_bench",
                "specialty": "General Medicine",  # will be classified later
                "icd10_code": None,
                "icd10_desc": None,
                "note_type": "full_encounter",
                "note_text": row.get("note", ""),
                "dialogue": row.get("src", ""),
                "chief_complaint": row.get("cc", ""),
                "gender": row.get("gender", ""),
                "patient_name": f"{row.get('patient_firstname','')} {row.get('patient_familyname','')}".strip(),
                "doctor_name": row.get("doctor_name", ""),
                "word_count": len(row.get("note", "").split()),
                "quality_tier": "primary",  # expert-created
            }
            write_jsonl(OUTPUT, record)
            aci_count += 1

    print(f"  ACI-Bench: {aci_count} encounters added")


total = count_jsonl(OUTPUT)
print(f"\n✓ Note pool complete: {total} total notes")
print(f"  Output: {OUTPUT}")
```

---

## Script 03 — Match and Score

**File:** `data_prep/scripts/03_match_and_score.py`

For every Synthea patient and each of their encounters, find the best-matching
note from the pool. Score each match. Store all results for selection.

```python
"""
03_match_and_score.py

Matches Synthea patients and encounters to notes in the pool.
Produces per-encounter match scores and per-patient quality scores.
Output: data/staging/match_results.jsonl
"""

from pathlib import Path
import pandas as pd
import json
from tqdm import tqdm
from datetime import datetime
from collections import defaultdict
from utils.mappings import SNOMED_TO_ICD10, ICD10_TO_SPECIALTY
from utils.io_utils import write_jsonl, load_jsonl
from utils.synthea_utils import load_synthea, get_active_conditions, get_active_medications

SYNTHEA_DIR = Path("data/raw/synthea/csv")
NOTE_POOL   = Path("data/staging/note_pool.jsonl")
OUTPUT      = Path("data/staging/match_results.jsonl")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.unlink(missing_ok=True)


# ─── Load data ────────────────────────────────────────────────────────────────
print("Loading Synthea data...")
synthea = load_synthea(SYNTHEA_DIR)

print("Loading note pool...")
notes = list(load_jsonl(NOTE_POOL))

# Index notes by specialty for fast lookup
notes_by_specialty = defaultdict(list)
for note in notes:
    notes_by_specialty[note["specialty"]].append(note)
notes_by_specialty["General Medicine"].extend(notes)  # always include general


# ─── Scoring function ─────────────────────────────────────────────────────────
def score_match(encounter: dict, note: dict) -> float:
    score = 0.0

    # 1. Specialty match (0.40)
    if note["specialty"] == encounter["specialty"]:
        score += 0.40
    elif note["specialty"] == "General Medicine":
        score += 0.10  # partial credit

    # 2. ICD-10 exact or parent match (0.35)
    note_icd = note.get("icd10_code", "") or ""
    enc_icd_list = encounter.get("icd10_codes", [])
    if note_icd and enc_icd_list:
        for enc_icd in enc_icd_list:
            if enc_icd and note_icd[:3] == enc_icd[:3]:
                score += 0.35
                break
            elif enc_icd and note_icd[0] == enc_icd[0]:
                score += 0.15
                break

    # 3. Condition keyword overlap (0.15)
    conditions = encounter.get("conditions", [])
    note_text  = (note.get("note_text", "") or "").lower()
    if conditions:
        matched = sum(
            1 for c in conditions
            if c.lower() in note_text or
               any(word in note_text for word in c.lower().split() if len(word) > 4)
        )
        score += 0.15 * (matched / len(conditions))

    # 4. Has dialogue (bonus for current encounter use)
    if note.get("dialogue"):
        score += 0.05

    # 5. Quality tier bonus
    tier_weights = {"primary": 0.05, "secondary": 0.02, "fallback": 0.0}
    score += tier_weights.get(note.get("quality_tier", "fallback"), 0)

    return round(min(score, 1.0), 3)


# ─── Match all patients ───────────────────────────────────────────────────────
print(f"\nMatching {len(synthea['patients'])} patients to note pool...")

patients_df   = synthea["patients"]
encounters_df = synthea["encounters"]
conditions_df = synthea["conditions"]
meds_df       = synthea["medications"]
obs_df        = synthea["observations"]

patient_quality_scores = {}

for patient_id in tqdm(patients_df["Id"].unique()):
    pt_encounters = encounters_df[
        encounters_df["PATIENT"] == patient_id
    ].sort_values("START")

    if len(pt_encounters) < 3:
        continue  # skip patients with too few encounters

    pt_row = patients_df[patients_df["Id"] == patient_id].iloc[0]
    birth_date = pd.to_datetime(pt_row["BIRTHDATE"])
    gender = pt_row["GENDER"]

    encounter_scores = []

    for _, enc in pt_encounters.iterrows():
        enc_date = pd.to_datetime(enc["START"])
        age = int((enc_date - birth_date).days / 365.25)

        # Get active conditions and medications at this encounter date
        active_conditions = get_active_conditions(conditions_df, patient_id, enc_date)
        active_meds       = get_active_medications(meds_df, patient_id, enc_date)
        recent_obs        = obs_df[
            (obs_df["PATIENT"] == patient_id) &
            (pd.to_datetime(obs_df["DATE"]) <= enc_date)
        ].tail(10)

        # Map SNOMED → ICD-10
        icd10_codes = list(filter(None, [
            SNOMED_TO_ICD10.get(str(code))
            for code in active_conditions["CODE"].tolist()
        ]))

        # Derive specialty
        specialty = ICD10_TO_SPECIALTY.get(
            icd10_codes[0][0] if icd10_codes else "X",
            "General Medicine"
        )

        encounter_record = {
            "patient_id":       patient_id,
            "encounter_id":     enc["Id"],
            "encounter_date":   enc_date.isoformat(),
            "encounter_reason": enc.get("REASONDESCRIPTION", ""),
            "specialty":        specialty,
            "age":              age,
            "gender":           gender,
            "icd10_codes":      icd10_codes,
            "conditions":       active_conditions["DESCRIPTION"].tolist(),
            "medications":      active_meds["DESCRIPTION"].tolist(),
            "recent_obs":       recent_obs[["DESCRIPTION", "VALUE", "UNITS"]].to_dict("records"),
        }

        # Find best matching note
        candidates = notes_by_specialty.get(specialty, []) + \
                     notes_by_specialty.get("General Medicine", [])[:50]

        best_note  = None
        best_score = 0.0

        for note in candidates:
            s = score_match(encounter_record, note)
            if s > best_score:
                best_score = s
                best_note  = note

        encounter_scores.append(best_score)

        write_jsonl(OUTPUT, {
            **encounter_record,
            "best_note_id":     best_note["note_id"] if best_note else None,
            "best_note_source": best_note["source"] if best_note else None,
            "best_note_text":   best_note["note_text"] if best_note else None,
            "best_note_dialogue": best_note.get("dialogue") if best_note else None,
            "match_score":      best_score,
        })

    # Patient quality = average match score across all encounters
    patient_quality_scores[patient_id] = (
        sum(encounter_scores) / len(encounter_scores)
        if encounter_scores else 0.0
    )

print(f"\n✓ Matching complete")
print(f"  Output: {OUTPUT}")
print(f"  Avg match quality: {sum(patient_quality_scores.values())/len(patient_quality_scores):.3f}")
```

---

## Script 04 — Select Top 50 Patients

**File:** `data_prep/scripts/04_select_patients.py`

```python
"""
04_select_patients.py

Selects the top 50 patients by match quality with specialty distribution constraint.
Output: data/staging/selected_patients.jsonl
"""

from pathlib import Path
from collections import defaultdict
from utils.io_utils import load_jsonl, write_jsonl, load_jsonl_as_df
from utils.mappings import ICD10_TO_SPECIALTY
import pandas as pd

MATCH_RESULTS = Path("data/staging/match_results.jsonl")
OUTPUT        = Path("data/staging/selected_patients.jsonl")
OUTPUT.unlink(missing_ok=True)

TARGET_TOTAL            = 50
MAX_PER_SPECIALTY       = 6
MIN_ENCOUNTERS          = 3
MIN_AVG_MATCH_SCORE     = 0.35

# Load and compute patient-level scores
results = list(load_jsonl(MATCH_RESULTS))

patient_data = defaultdict(lambda: {
    "encounters": [], "scores": [], "specialties": []
})

for r in results:
    pid = r["patient_id"]
    patient_data[pid]["encounters"].append(r)
    patient_data[pid]["scores"].append(r["match_score"])
    patient_data[pid]["specialties"].append(r["specialty"])

# Score and filter patients
scored_patients = []
for pid, data in patient_data.items():
    encounter_count = len(data["encounters"])
    avg_score = sum(data["scores"]) / len(data["scores"])

    if encounter_count < MIN_ENCOUNTERS:
        continue
    if avg_score < MIN_AVG_MATCH_SCORE:
        continue
    if not any(r["conditions"] for r in data["encounters"]):
        continue  # skip patients with no conditions

    # Primary specialty = most common across encounters
    from collections import Counter
    primary_specialty = Counter(data["specialties"]).most_common(1)[0][0]

    scored_patients.append({
        "patient_id":        pid,
        "quality_score":     round(avg_score, 3),
        "encounter_count":   encounter_count,
        "primary_specialty": primary_specialty,
        "has_dialogue":      any(r.get("best_note_dialogue") for r in data["encounters"]),
    })

# Sort by quality score descending
scored_patients.sort(key=lambda x: x["quality_score"], reverse=True)

# Select top 50 with specialty distribution
selected = []
specialty_counts = defaultdict(int)

for patient in scored_patients:
    specialty = patient["primary_specialty"]
    if specialty_counts[specialty] >= MAX_PER_SPECIALTY:
        continue
    selected.append(patient)
    specialty_counts[specialty] += 1
    if len(selected) >= TARGET_TOTAL:
        break

# Write output
for p in selected:
    write_jsonl(OUTPUT, p)

# Report
print(f"\n✓ Selected {len(selected)} patients")
print(f"\nSpecialty distribution:")
for spec, count in sorted(specialty_counts.items(), key=lambda x: -x[1]):
    print(f"  {spec:<30} {count}")
print(f"\nQuality score range: "
      f"{min(p['quality_score'] for p in selected):.3f} – "
      f"{max(p['quality_score'] for p in selected):.3f}")
print(f"\nOutput: {OUTPUT}")
```

---

## Script 05 — Adapt Notes via Groq

**File:** `data_prep/scripts/05_adapt_notes.py`

Uses Groq free tier (Llama 3.1 70B) to adapt matched notes to each patient's
specific Synthea data. Prior visit notes are adapted. Current (showcase) encounters
use ACI-Bench dialogue directly where available.

```python
"""
05_adapt_notes.py

Adapts matched notes to be coherent with each patient's Synthea record.
Uses Groq free tier: llama-3.1-70b-versatile
No cost. ~125 API calls. ~20-30 minutes total.

Set env var: export GROQ_API_KEY=your_key_here
Get free key: https://console.groq.com
"""

import os
import time
from pathlib import Path
from collections import defaultdict
from groq import Groq
from utils.io_utils import load_jsonl, write_jsonl
from utils.synthea_utils import load_synthea, compute_age

SELECTED    = Path("data/staging/selected_patients.jsonl")
MATCHES     = Path("data/staging/match_results.jsonl")
SYNTHEA_DIR = Path("data/raw/synthea/csv")
OUTPUT      = Path("data/staging/adapted_notes.jsonl")
OUTPUT.unlink(missing_ok=True)

client   = Groq(api_key=os.environ["GROQ_API_KEY"])
synthea  = load_synthea(SYNTHEA_DIR)
patients_df = synthea["patients"]

ADAPT_PROMPT = """\
You are a clinical documentation specialist. Adapt the REFERENCE NOTE below
to match the PATIENT DATA provided.

Rules:
- Keep the exact same section structure and format (SOAP or equivalent)
- Keep the clinical writing style and length of the reference note
- Replace any conditions, medications, or clinical details that conflict
  with the patient data
- Do not add conditions or medications not present in the patient data
- Do not invent lab values — only use the ones provided
- Write the note in the same tense and perspective as the reference

PATIENT DATA:
Age: {age}
Sex: {sex}
Visit date: {encounter_date}
Visit reason: {encounter_reason}
Active conditions: {conditions}
Current medications: {medications}
Recent observations: {observations}

REFERENCE NOTE:
{reference_note}

Write the adapted note now. Output only the note text, no preamble."""


def call_groq(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=900,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt+1} after error: {e}")
                time.sleep(2 ** attempt)
            else:
                raise


def format_observations(obs_list: list) -> str:
    if not obs_list:
        return "None recorded"
    lines = []
    for o in obs_list[:8]:
        val = o.get("VALUE", "")
        unit = o.get("UNITS", "")
        desc = o.get("DESCRIPTION", "")
        lines.append(f"- {desc}: {val} {unit}".strip())
    return "\n".join(lines)


# Index match results by patient_id
all_matches = list(load_jsonl(MATCHES))
matches_by_patient = defaultdict(list)
for m in all_matches:
    matches_by_patient[m["patient_id"]].append(m)

selected_patients = list(load_jsonl(SELECTED))
note_idx = 0

for patient in selected_patients:
    pid = patient["patient_id"]

    pt_row  = patients_df[patients_df["Id"] == pid].iloc[0]
    gender  = "Male" if pt_row["GENDER"] == "M" else "Female"

    # Sort encounters chronologically
    pt_matches = sorted(
        matches_by_patient[pid],
        key=lambda x: x["encounter_date"]
    )

    prior_visits   = pt_matches[:-1]   # all but last = prior history
    current_visit  = pt_matches[-1]    # last = the demo encounter

    print(f"\nPatient {pid} ({patient['primary_specialty']}, "
          f"{len(pt_matches)} encounters)")

    # ── Prior visits: adapt reference note ──────────────────────────────────
    for enc in prior_visits:
        if not enc.get("best_note_text"):
            print(f"  [{enc['encounter_date'][:10]}] No reference note — skipping")
            continue

        age = compute_age(pt_row["BIRTHDATE"], enc["encounter_date"])

        prompt = ADAPT_PROMPT.format(
            age=age,
            sex=gender,
            encounter_date=enc["encounter_date"][:10],
            encounter_reason=enc.get("encounter_reason", "Follow-up visit"),
            conditions=", ".join(enc.get("conditions", [])) or "None documented",
            medications=", ".join(enc.get("medications", [])) or "None documented",
            observations=format_observations(enc.get("recent_obs", [])),
            reference_note=enc["best_note_text"][:2500],
        )

        print(f"  [{enc['encounter_date'][:10]}] Adapting note "
              f"(source: {enc['best_note_source']}, "
              f"score: {enc['match_score']:.2f})...", end=" ")

        adapted_text = call_groq(prompt)

        write_jsonl(OUTPUT, {
            "adapted_note_id":    f"note_{note_idx:06d}",
            "encounter_id":       enc["encounter_id"],
            "patient_id":         pid,
            "encounter_date":     enc["encounter_date"],
            "note_text":          adapted_text,
            "reference_note_id":  enc["best_note_id"],
            "reference_source":   enc["best_note_source"],
            "match_score":        enc["match_score"],
            "is_showcase":        False,
            "has_dialogue":       False,
        })
        note_idx += 1
        print("done")

    # ── Current (showcase) visit: use ACI-Bench dialogue if available ──────
    has_aci = (
        current_visit.get("best_note_source") == "aci_bench" and
        current_visit.get("best_note_dialogue")
    )

    if has_aci:
        # Use ACI-Bench note and dialogue directly — no adaptation needed
        write_jsonl(OUTPUT, {
            "adapted_note_id":    f"note_{note_idx:06d}",
            "encounter_id":       current_visit["encounter_id"],
            "patient_id":         pid,
            "encounter_date":     current_visit["encounter_date"],
            "note_text":          current_visit["best_note_text"],
            "dialogue":           current_visit["best_note_dialogue"],
            "reference_note_id":  current_visit["best_note_id"],
            "reference_source":   "aci_bench",
            "match_score":        current_visit["match_score"],
            "is_showcase":        True,
            "has_dialogue":       True,
        })
        print(f"  [{current_visit['encounter_date'][:10]}] "
              f"Showcase → ACI-Bench dialogue attached")
    else:
        # Fall back to adapting the best matched note
        if current_visit.get("best_note_text"):
            age = compute_age(pt_row["BIRTHDATE"], current_visit["encounter_date"])
            prompt = ADAPT_PROMPT.format(
                age=age, sex=gender,
                encounter_date=current_visit["encounter_date"][:10],
                encounter_reason=current_visit.get("encounter_reason", "Follow-up"),
                conditions=", ".join(current_visit.get("conditions", [])) or "None",
                medications=", ".join(current_visit.get("medications", [])) or "None",
                observations=format_observations(current_visit.get("recent_obs", [])),
                reference_note=current_visit["best_note_text"][:2500],
            )
            adapted_text = call_groq(prompt)
            write_jsonl(OUTPUT, {
                "adapted_note_id":  f"note_{note_idx:06d}",
                "encounter_id":     current_visit["encounter_id"],
                "patient_id":       pid,
                "encounter_date":   current_visit["encounter_date"],
                "note_text":        adapted_text,
                "dialogue":         current_visit.get("best_note_dialogue"),
                "reference_source": current_visit["best_note_source"],
                "match_score":      current_visit["match_score"],
                "is_showcase":      True,
                "has_dialogue":     bool(current_visit.get("best_note_dialogue")),
            })
            print(f"  [{current_visit['encounter_date'][:10]}] "
                  f"Showcase → adapted note (no ACI dialogue)")
    note_idx += 1

print(f"\n✓ Adaptation complete: {note_idx} notes written to {OUTPUT}")
```

---

## Script 06 — Assemble Corpus

**File:** `data_prep/scripts/06_assemble_corpus.py`

Assembles all final JSONL files from Synthea data + adapted notes.

```python
"""
06_assemble_corpus.py

Assembles the final clinical corpus JSONL files.

Output files (data/clinical_corpus/):
  patients.jsonl
  encounters.jsonl
  notes.jsonl
  conditions.jsonl
  medications.jsonl
  observations.jsonl
  dialogues.jsonl
  source_provenance.jsonl
  manifest.json
"""

from pathlib import Path
from collections import defaultdict
import pandas as pd
import json
from datetime import datetime, timezone
from utils.io_utils import load_jsonl, write_jsonl
from utils.synthea_utils import load_synthea, compute_age
from utils.mappings import SNOMED_TO_ICD10, ICD10_TO_SPECIALTY

CORPUS_DIR  = Path("data/clinical_corpus")
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Clear existing corpus files
for f in CORPUS_DIR.glob("*.jsonl"):
    f.unlink()

SELECTED_PATH = Path("data/staging/selected_patients.jsonl")
NOTES_PATH    = Path("data/staging/adapted_notes.jsonl")
MATCHES_PATH  = Path("data/staging/match_results.jsonl")
SYNTHEA_DIR   = Path("data/raw/synthea/csv")

synthea     = load_synthea(SYNTHEA_DIR)
selected    = {p["patient_id"]: p for p in load_jsonl(SELECTED_PATH)}
notes       = {n["encounter_id"]: n for n in load_jsonl(NOTES_PATH)}
matches_raw = list(load_jsonl(MATCHES_PATH))
matches     = {m["encounter_id"]: m for m in matches_raw
               if m["patient_id"] in selected}

patients_df   = synthea["patients"]
encounters_df = synthea["encounters"]
conditions_df = synthea["conditions"]
meds_df       = synthea["medications"]
obs_df        = synthea["observations"]

counts = defaultdict(int)

# ── patients.jsonl ─────────────────────────────────────────────────────────────
print("Writing patients.jsonl...")
for pid, meta in selected.items():
    pt = patients_df[patients_df["Id"] == pid].iloc[0]
    birth_dt = pd.to_datetime(pt["BIRTHDATE"])

    write_jsonl(CORPUS_DIR / "patients.jsonl", {
        "patient_id":         pid,
        "birth_year":         birth_dt.year,
        "sex":                pt["GENDER"],
        "race":               pt.get("RACE", ""),
        "ethnicity":          pt.get("ETHNICITY", ""),
        "primary_specialty":  meta["primary_specialty"],
        "encounter_count":    meta["encounter_count"],
        "quality_score":      meta["quality_score"],
        "synthetic_source":   "synthea_v3",
    })
    counts["patients"] += 1

# ── encounters.jsonl ────────────────────────────────────────────────────────────
print("Writing encounters.jsonl...")
for enc_id, match in matches.items():
    note = notes.get(enc_id, {})
    write_jsonl(CORPUS_DIR / "encounters.jsonl", {
        "encounter_id":    enc_id,
        "patient_id":      match["patient_id"],
        "encounter_date":  match["encounter_date"],
        "specialty":       match["specialty"],
        "reason":          match.get("encounter_reason", ""),
        "match_score":     match["match_score"],
        "is_showcase":     note.get("is_showcase", False),
        "has_dialogue":    note.get("has_dialogue", False),
    })
    counts["encounters"] += 1

# ── notes.jsonl ────────────────────────────────────────────────────────────────
print("Writing notes.jsonl...")
for enc_id, note in notes.items():
    if note.get("patient_id") not in selected:
        continue
    write_jsonl(CORPUS_DIR / "notes.jsonl", {
        "note_id":          note["adapted_note_id"],
        "encounter_id":     enc_id,
        "patient_id":       note["patient_id"],
        "note_text":        note["note_text"],
        "reference_source": note.get("reference_source", ""),
        "reference_note_id":note.get("reference_note_id", ""),
        "is_showcase":      note.get("is_showcase", False),
    })
    counts["notes"] += 1

# ── dialogues.jsonl ────────────────────────────────────────────────────────────
print("Writing dialogues.jsonl...")
dlg_idx = 0
for enc_id, note in notes.items():
    if not note.get("has_dialogue") or not note.get("dialogue"):
        continue
    if note.get("patient_id") not in selected:
        continue
    write_jsonl(CORPUS_DIR / "dialogues.jsonl", {
        "dialogue_id":      f"dlg_{dlg_idx:06d}",
        "encounter_id":     enc_id,
        "patient_id":       note["patient_id"],
        "dialogue_text":    note["dialogue"],
        "source":           note.get("reference_source", ""),
        "is_showcase":      note.get("is_showcase", False),
    })
    dlg_idx += 1
    counts["dialogues"] += 1

# ── conditions.jsonl ───────────────────────────────────────────────────────────
print("Writing conditions.jsonl...")
cond_idx = 0
for pid in selected:
    pt_conds = conditions_df[conditions_df["PATIENT"] == pid]
    for _, cond in pt_conds.iterrows():
        write_jsonl(CORPUS_DIR / "conditions.jsonl", {
            "condition_id":   f"cond_{cond_idx:06d}",
            "patient_id":     pid,
            "snomed_code":    str(cond["CODE"]),
            "icd10_code":     SNOMED_TO_ICD10.get(str(cond["CODE"]), ""),
            "description":    cond["DESCRIPTION"],
            "onset_date":     str(cond["START"])[:10],
            "stop_date":      str(cond["STOP"])[:10] if pd.notna(cond["STOP"]) else None,
            "is_active":      pd.isna(cond["STOP"]),
        })
        cond_idx += 1
        counts["conditions"] += 1

# ── medications.jsonl ──────────────────────────────────────────────────────────
print("Writing medications.jsonl...")
med_idx = 0
for pid in selected:
    pt_meds = meds_df[meds_df["PATIENT"] == pid]
    for _, med in pt_meds.iterrows():
        write_jsonl(CORPUS_DIR / "medications.jsonl", {
            "medication_id":  f"med_{med_idx:06d}",
            "patient_id":     pid,
            "rxnorm_code":    str(med.get("CODE", "")),
            "description":    med["DESCRIPTION"],
            "start_date":     str(med["START"])[:10],
            "stop_date":      str(med["STOP"])[:10] if pd.notna(med.get("STOP")) else None,
            "is_active":      pd.isna(med.get("STOP")),
            "reason":         med.get("REASONDESCRIPTION", ""),
        })
        med_idx += 1
        counts["medications"] += 1

# ── observations.jsonl ─────────────────────────────────────────────────────────
print("Writing observations.jsonl...")
obs_idx = 0
for pid in selected:
    pt_obs = obs_df[obs_df["PATIENT"] == pid]
    for _, ob in pt_obs.iterrows():
        write_jsonl(CORPUS_DIR / "observations.jsonl", {
            "observation_id": f"obs_{obs_idx:06d}",
            "patient_id":     pid,
            "encounter_id":   ob.get("ENCOUNTER", ""),
            "loinc_code":     str(ob.get("CODE", "")),
            "description":    ob["DESCRIPTION"],
            "value":          str(ob.get("VALUE", "")),
            "units":          ob.get("UNITS", ""),
            "date":           str(ob["DATE"])[:10],
        })
        obs_idx += 1
        counts["observations"] += 1

# ── source_provenance.jsonl ────────────────────────────────────────────────────
print("Writing source_provenance.jsonl...")
for enc_id, match in matches.items():
    note = notes.get(enc_id, {})
    write_jsonl(CORPUS_DIR / "source_provenance.jsonl", {
        "encounter_id":     enc_id,
        "patient_id":       match["patient_id"],
        "note_source":      note.get("reference_source", "none"),
        "reference_note_id":note.get("reference_note_id", ""),
        "match_score":      match["match_score"],
        "adapted_by":       "llama-3.1-70b-versatile" if not note.get("is_showcase") or note.get("reference_source") != "aci_bench" else "aci_bench_direct",
        "is_showcase":      note.get("is_showcase", False),
    })

# ── manifest.json ──────────────────────────────────────────────────────────────
manifest = {
    "corpus_name":        "Scribe-IQ Clinical Corpus v1.0",
    "generated_at":       datetime.now(timezone.utc).isoformat(),
    "synthea_seed":       42,
    "synthea_population": 1000,
    "selected_patients":  counts["patients"],
    "record_counts":      dict(counts),
    "sources": {
        "patient_spine":  "Synthea v3 (seed=42)",
        "note_pool":      "MTSamples (CC0), MedSynth (HF), ACI-Bench (CC BY)",
        "note_adaptation":"Groq / llama-3.1-70b-versatile",
    },
    "files": [str(f.name) for f in sorted(CORPUS_DIR.glob("*.jsonl"))],
}

with open(CORPUS_DIR / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print(f"\n✓ Corpus assembled")
for entity, count in counts.items():
    print(f"  {entity:<20} {count:>6} records")
print(f"\n  Output: {CORPUS_DIR}/")
```

---

## Script 07 — Validate Corpus

**File:** `data_prep/scripts/07_validate_corpus.py`

```python
"""
07_validate_corpus.py

Validates the assembled corpus:
- Referential integrity (all foreign keys resolve)
- No empty note texts
- Specialty distribution
- Match score distribution
- Note source breakdown
- Showcase encounters have dialogues
Produces: data/clinical_corpus/audit_report.md
"""

from pathlib import Path
from collections import defaultdict, Counter
import json
from utils.io_utils import load_jsonl

CORPUS = Path("data/clinical_corpus")
issues = []
warnings = []

print("Running corpus validation...\n")

# Load all files
patients    = list(load_jsonl(CORPUS / "patients.jsonl"))
encounters  = list(load_jsonl(CORPUS / "encounters.jsonl"))
notes       = list(load_jsonl(CORPUS / "notes.jsonl"))
dialogues   = list(load_jsonl(CORPUS / "dialogues.jsonl"))
conditions  = list(load_jsonl(CORPUS / "conditions.jsonl"))
medications = list(load_jsonl(CORPUS / "medications.jsonl"))

patient_ids   = {p["patient_id"] for p in patients}
encounter_ids = {e["encounter_id"] for e in encounters}

# ── Referential integrity ──────────────────────────────────────────────────────
for enc in encounters:
    if enc["patient_id"] not in patient_ids:
        issues.append(f"Encounter {enc['encounter_id']} has unknown patient_id")

for note in notes:
    if note["encounter_id"] not in encounter_ids:
        issues.append(f"Note {note['note_id']} has unknown encounter_id")
    if not note.get("note_text") or len(note["note_text"]) < 50:
        issues.append(f"Note {note['note_id']} has empty or very short text")

for dlg in dialogues:
    if dlg["encounter_id"] not in encounter_ids:
        issues.append(f"Dialogue {dlg['dialogue_id']} has unknown encounter_id")

# ── Showcase encounters have dialogues ─────────────────────────────────────────
showcase_encs = {e["encounter_id"] for e in encounters if e.get("is_showcase")}
dialogue_encs = {d["encounter_id"] for d in dialogues}
missing_dlg   = showcase_encs - dialogue_encs
for enc_id in missing_dlg:
    warnings.append(f"Showcase encounter {enc_id} has no dialogue")

# ── Stats ──────────────────────────────────────────────────────────────────────
specialty_dist  = Counter(p["primary_specialty"] for p in patients)
source_dist     = Counter(n["reference_source"] for n in notes)
score_vals      = [e["match_score"] for e in encounters]
avg_score       = sum(score_vals) / len(score_vals) if score_vals else 0
enc_per_patient = Counter(e["patient_id"] for e in encounters)

# ── Print report ───────────────────────────────────────────────────────────────
print(f"{'='*50}")
print(f"CORPUS AUDIT REPORT")
print(f"{'='*50}\n")

print(f"SCALE")
print(f"  Patients:     {len(patients)}")
print(f"  Encounters:   {len(encounters)}")
print(f"  Notes:        {len(notes)}")
print(f"  Dialogues:    {len(dialogues)}")
print(f"  Conditions:   {len(conditions)}")
print(f"  Medications:  {len(medications)}")

print(f"\nSPECIALTY DISTRIBUTION")
for spec, count in sorted(specialty_dist.items(), key=lambda x: -x[1]):
    print(f"  {spec:<30} {count}")

print(f"\nNOTE SOURCE BREAKDOWN")
for source, count in sorted(source_dist.items(), key=lambda x: -x[1]):
    print(f"  {source:<20} {count}")

print(f"\nMATCH QUALITY")
print(f"  Avg score:    {avg_score:.3f}")
print(f"  Min score:    {min(score_vals):.3f}")
print(f"  Max score:    {max(score_vals):.3f}")

print(f"\nENCOUNTERS PER PATIENT")
enc_counts = list(enc_per_patient.values())
print(f"  Min: {min(enc_counts)}  Max: {max(enc_counts)}  "
      f"Avg: {sum(enc_counts)/len(enc_counts):.1f}")

print(f"\nSHOWCASE ENCOUNTERS")
print(f"  Total showcase:         {len(showcase_encs)}")
print(f"  With ACI-Bench dialogue:{len(dialogue_encs)}")
print(f"  Missing dialogue:       {len(missing_dlg)}")

if issues:
    print(f"\nISSUES ({len(issues)}):")
    for issue in issues:
        print(f"  ✗ {issue}")
else:
    print(f"\n✓ No integrity issues found")

if warnings:
    print(f"\nWARNINGS ({len(warnings)}):")
    for warning in warnings:
        print(f"  ⚠ {warning}")

# Write audit report markdown
report = f"""# Scribe-IQ Corpus Audit Report

## Scale
| Entity | Count |
|---|---|
| Patients | {len(patients)} |
| Encounters | {len(encounters)} |
| Notes | {len(notes)} |
| Dialogues | {len(dialogues)} |
| Conditions | {len(conditions)} |
| Medications | {len(medications)} |

## Specialty Distribution
{chr(10).join(f'| {s} | {c} |' for s, c in sorted(specialty_dist.items()))}

## Note Source Breakdown
{chr(10).join(f'| {s} | {c} |' for s, c in sorted(source_dist.items()))}

## Match Quality
- Average: {avg_score:.3f}
- Range: {min(score_vals):.3f} – {max(score_vals):.3f}

## Issues
{"None" if not issues else chr(10).join(f'- {i}' for i in issues)}

## Warnings
{"None" if not warnings else chr(10).join(f'- {w}' for w in warnings)}
"""

(CORPUS / "audit_report.md").write_text(report)
print(f"\n  Audit report: {CORPUS}/audit_report.md")
```

---

## Utility Modules

### `utils/mappings.py`

```python
# SNOMED CT → ICD-10 for top Synthea conditions
SNOMED_TO_ICD10 = {
    "44054006":  "E11.9",   # Type 2 diabetes mellitus
    "38341003":  "I10",     # Essential hypertension
    "53741008":  "I25.10",  # Coronary artery disease
    "195967001": "J45.909", # Asthma
    "13645005":  "J44.1",   # COPD
    "40055000":  "N18.3",   # CKD stage 3
    "84757009":  "G40.909", # Epilepsy
    "64859006":  "M81.0",   # Osteoporosis
    "396275006": "M19.90",  # Osteoarthritis
    "73211009":  "E11.9",   # Diabetes mellitus
    "49436004":  "I48.91",  # Atrial fibrillation
    "230690007": "I63.9",   # Stroke
    "93761005":  "C18.9",   # Colorectal cancer
    "34000006":  "K50.90",  # Crohn's disease
    "40122008":  "J18.9",   # Pneumonia
    "195662009": "J06.9",   # Acute URI
    "271737000": "D64.9",   # Anemia
    "36971009":  "J32.9",   # Sinusitis
    "162864005": "E66.9",   # Obesity
    "55822004":  "E78.5",   # Hyperlipidemia
    "15777000":  "K21.0",   # GERD
    "26929004":  "G30.9",   # Alzheimer's
    "35489007":  "F32.9",   # Depression
    "197480006": "F41.1",   # Anxiety
    "363346000": "C80.1",   # Malignant neoplasm
    "73595000":  "E03.9",   # Hypothyroidism
    "415068001": "L40.0",   # Psoriasis
    "69896004":  "M06.9",   # Rheumatoid arthritis
    "267102003": "J45.20",  # Mild intermittent asthma
    "59621000":  "I10",     # Hypertension NOS
    "9855000":   "N40.1",   # BPH
    "90688005":  "N18.9",   # CKD NOS
    "44054006":  "E11.9",   # T2DM NOS
    "46635009":  "E10.9",   # Type 1 diabetes
    "237599002": "E66.01",  # Morbid obesity
    "703151001": "J45.51",  # Moderate persistent asthma
    "444814009": "J06.9",   # Viral upper respiratory infection
    "62106007":  "N10",     # Acute pyelonephritis
    "57870002":  "N39.0",   # Urinary tract infection
    "43878008":  "J02.9",   # Strep throat
    "3928004":   "H66.90",  # Otitis media
    "233604007": "J15.9",   # Pneumonia NOS
    "11840006":  "N20.0",   # Kidney stone
    "370143000": "M54.5",   # Low back pain
    "298705000": "M79.3",   # Panniculitis
    "50043002":  "J96.00",  # Respiratory failure
}

# ICD-10 first character → specialty
ICD10_TO_SPECIALTY = {
    "A": "Infectious Disease", "B": "Infectious Disease",
    "C": "Oncology",
    "D": "Hematology",
    "E": "Endocrinology",
    "F": "Psychiatry",
    "G": "Neurology",
    "H": "Ophthalmology",
    "I": "Cardiology",
    "J": "Pulmonology",
    "K": "Gastroenterology",
    "L": "Dermatology",
    "M": "Orthopedics",
    "N": "Nephrology",
    "O": "Obstetrics",
    "Q": "Pediatrics",
    "R": "General Medicine",
    "S": "Orthopedics",
    "T": "Emergency Medicine",
    "Z": "General Medicine",
}

# MTSamples specialty → Standard specialty name
MTSAMPLES_TO_STANDARD_SPECIALTY = {
    "Cardiovascular / Pulmonary": "Cardiology",
    "Neurology":                  "Neurology",
    "Orthopedic":                 "Orthopedics",
    "Gastroenterology":           "Gastroenterology",
    "Urology":                    "Urology",
    "Nephrology":                 "Nephrology",
    "Psychiatry / Psychology":    "Psychiatry",
    "Dermatology":                "Dermatology",
    "Endocrinology":              "Endocrinology",
    "Ophthalmology":              "Ophthalmology",
    "ENT - Otolaryngology":       "Otorhinolaryngology",
    "General Medicine":           "General Medicine",
    "Obstetrics / Gynecology":    "Obstetrics",
    "Pediatrics - Neonatal":      "Pediatrics",
    "Rheumatology":               "Orthopedics",
    "Hematology - Oncology":      "Oncology",
    "Pulmonology":                "Pulmonology",
    "SOAP / Chart / Progress Notes": "General Medicine",
    "Office Notes":               "General Medicine",
    "Consult - History and Phy.": "General Medicine",
}
```

### `utils/io_utils.py`

```python
import json
from pathlib import Path

def write_jsonl(path: Path, record: dict):
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")

def load_jsonl(path: Path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for line in f if line.strip())
```

### `utils/synthea_utils.py`

```python
import pandas as pd
from pathlib import Path
from datetime import datetime

def load_synthea(csv_dir: Path) -> dict:
    return {
        "patients":   pd.read_csv(csv_dir / "patients.csv"),
        "encounters": pd.read_csv(csv_dir / "encounters.csv"),
        "conditions": pd.read_csv(csv_dir / "conditions.csv"),
        "medications": pd.read_csv(csv_dir / "medications.csv"),
        "observations": pd.read_csv(csv_dir / "observations.csv"),
    }

def get_active_conditions(df, patient_id, as_of_date):
    mask = (
        (df["PATIENT"] == patient_id) &
        (pd.to_datetime(df["START"]) <= as_of_date) &
        (df["STOP"].isna() | (pd.to_datetime(df["STOP"]) >= as_of_date))
    )
    return df[mask]

def get_active_medications(df, patient_id, as_of_date):
    mask = (
        (df["PATIENT"] == patient_id) &
        (pd.to_datetime(df["START"]) <= as_of_date) &
        (df["STOP"].isna() | (pd.to_datetime(df["STOP"]) >= as_of_date))
    )
    return df[mask]

def compute_age(birth_date_str: str, as_of_date_str: str) -> int:
    birth = pd.to_datetime(birth_date_str)
    as_of = pd.to_datetime(as_of_date_str)
    return int((as_of - birth).days / 365.25)
```

---

## requirements.txt

```
datasets>=2.14.0
pandas>=2.0.0
groq>=0.9.0
tqdm>=4.65.0
```

---

## README — Data Prep

```markdown
# Scribe-IQ Data Pipeline

Generates a synthetic clinical corpus of 50 patients for the Scribe-IQ demo.

## Setup

```bash
pip install -r requirements.txt

# Download Synthea
curl -L https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar \
     -o synthea-with-dependencies.jar

# Set Groq API key (free at console.groq.com)
export GROQ_API_KEY=your_key_here

# Clone ACI-Bench
git clone https://github.com/microsoft/clinical_visit_note_summarization_corpus \
          data/raw/aci_bench
```

## Run the pipeline

```bash
# Step 1: Generate 1000 Synthea patients (~5 min)
bash scripts/01_generate_patients.sh

# Step 2: Build note pool from MedSynth + MTSamples + ACI-Bench (~30 min)
python scripts/02_build_note_pool.py

# Step 3: Match all patients to notes (~45 min on M1 Max)
python scripts/03_match_and_score.py

# Step 4: Select top 50 patients (seconds)
python scripts/04_select_patients.py

# Step 5: Adapt notes via Groq (~20 min, free)
python scripts/05_adapt_notes.py

# Step 6: Assemble final corpus files (~5 min)
python scripts/06_assemble_corpus.py

# Step 7: Validate and generate audit report (~1 min)
python scripts/07_validate_corpus.py
```

## Output

```
data/clinical_corpus/
  patients.jsonl        50 patients
  encounters.jsonl      ~250 encounters
  notes.jsonl           ~200 notes
  dialogues.jsonl       ~50 dialogues
  conditions.jsonl      ~400 conditions
  medications.jsonl     ~500 medications
  observations.jsonl    ~2000 observations
  source_provenance.jsonl
  manifest.json
  audit_report.md
  dataset_card.md
```

## Data Sources

| Source | License | Role |
|---|---|---|
| Synthea | Apache 2.0 | Patient spine |
| MedSynth | HuggingFace | ICD-10 coded SOAP notes |
| MTSamples | CC0 | Human-written progress notes |
| ACI-Bench | CC BY 4.0 | Expert dialogue-note pairs |
```

---

## Execution Order for Cursor

Paste this entire document into Cursor as a project brief. Then ask Cursor to:

1. `Create the full repository structure`
2. `Implement utils/mappings.py, utils/io_utils.py, utils/synthea_utils.py`
3. `Implement scripts/01 through 07 one at a time`
4. `Run script 01 and show me the output`
5. Continue sequentially through all scripts

Each script is self-contained and can be debugged independently.
The pipeline is resumable — each script reads from the previous script's output.
