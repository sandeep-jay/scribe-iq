# Scribe-IQ — Data Generation Pipeline v2
## Implementation Brief (Reviewed + Corrected)

---

## Corrections Applied from Review

1. General Medicine candidate list — no longer appends full pool, uses capped sample
2. Working directory — all scripts run from `data_prep/`, PYTHONPATH set explicitly
3. `load_jsonl_as_df` import removed from Script 04
4. MedSynth ICD-10 — defensive string normalizer added
5. Duplicate SNOMED key `44054006` fixed in mappings.py
6. Validation metrics — showcase vs ACI dialogue counts labeled precisely
7. `dataset_card.md` — generator script added (Script 08)
8. Groq model — pinned with a note to check Groq docs at build time
9. Repo layout — canonical path decision documented at top
10. ACI-Bench showcase — reserved assignment step added before match/score
11. LLM adaptation — condition/medication allowlist check added post-generation
12. Synthea modules — validated against known v3 module names

---

## Repo Layout Decision

```
scribe-iq/                          ← repo root
  reference-docs/                   ← architecture proposals + long-form references
    CLINICAL_LAKEHOUSE_PROPOSAL_V2.md
    ...

  data_prep/                        ← CANONICAL: offline corpus builder for this repo
    scripts/
    utils/
    requirements.txt
    README.md

  data/                             ← shared data dir
    raw/
    staging/
    clinical_corpus/

  backend/
  frontend/
```

**Rule:** **`data_prep/`** is the **only supported** tree for running corpus-generation scripts. **Historical** lakehouse-style proposals live under **`reference-docs/`** (see **`docs/history/EVOLUTION.md`**). An optional local **`lakehouse-old/`** directory may exist on some machines and is **not** part of the supported layout.

---

## Working Directory Convention

All scripts are run from the `data_prep/` directory:

```bash
cd scribe-iq/data_prep
python scripts/02_build_note_pool.py
```

The `utils/` package is a sibling of `scripts/` inside `data_prep/`, so Python
resolves imports correctly when run from `data_prep/`.

Alternatively, add to shell profile:
```bash
export PYTHONPATH="/path/to/scribe-iq/data_prep:$PYTHONPATH"
```

---

## Full Repository Structure

```
scribe-iq/
  data_prep/
    scripts/
      01_generate_patients.sh
      02_build_note_pool.py
      03_reserve_aci_encounters.py   ← NEW: reserve ACI-Bench before matching
      04_match_and_score.py
      05_select_patients.py
      06_adapt_notes.py
      07_assemble_corpus.py
      08_generate_dataset_card.py    ← NEW: generates dataset_card.md
      09_validate_corpus.py
    utils/
      __init__.py
      mappings.py
      io_utils.py
      synthea_utils.py
      scoring.py
      note_checks.py                 ← NEW: allowlist validation post-adaptation
    requirements.txt
    README.md
  data/
    raw/
      synthea/
      aci_bench/
    staging/
      note_pool.jsonl
      aci_reservations.jsonl         ← NEW
      match_results.jsonl
      selected_patients.jsonl
      adapted_notes.jsonl
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
  reference-docs/
    CLINICAL_LAKEHOUSE_PROPOSAL_V2.md
```

---

## Script 01 — Generate Patients

**File:** `data_prep/scripts/01_generate_patients.sh`

```bash
#!/bin/bash
# Generates 1000 synthetic patients via Synthea
# Requires: Java 11+
# Download JAR: https://github.com/synthetichealth/synthea/releases
#   → synthea-with-dependencies.jar → place in scribe-iq/ root
#
# VALIDATED module names for Synthea v3 (check release notes if generation fails):
#   heart_disease, hypertension, diabetes, stroke, epilepsy,
#   colorectal_cancer, crohns_disease, osteoporosis, osteoarthritis,
#   asthma, copd, kidney_disease, dermatitis, hypothyroidism,
#   anxiety_and_panic, depression, lung_cancer, atrial_fibrillation,
#   alzheimers_disease, rheumatoid_arthritis
#
# NOTE: module names are file names in synthea/src/main/resources/modules/
# If a module fails, check the exact filename in that directory.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"
JAR="$REPO_ROOT/synthea-with-dependencies.jar"
OUTPUT_DIR="$REPO_ROOT/data/raw/synthea"

if [ ! -f "$JAR" ]; then
    echo "ERROR: synthea-with-dependencies.jar not found at $JAR"
    echo "Download from: https://github.com/synthetichealth/synthea/releases"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

java -jar "$JAR" \
  -p 1000 \
  -s 42 \
  --exporter.csv.export true \
  --exporter.fhir.export false \
  --exporter.baseDirectory "$OUTPUT_DIR" \
  -m "heart_disease,hypertension,diabetes,stroke,epilepsy,\
colorectal_cancer,crohns_disease,osteoporosis,\
osteoarthritis,asthma,copd,kidney_disease,\
dermatitis,hypothyroidism,anxiety_and_panic,depression,\
lung_cancer,atrial_fibrillation,alzheimers_disease,\
rheumatoid_arthritis"

echo ""
echo "✓ Synthea generation complete"
echo "  Output: $OUTPUT_DIR/csv/"
ls -lh "$OUTPUT_DIR/csv/"
```

---

## Script 02 — Build Note Pool

**File:** `data_prep/scripts/02_build_note_pool.py`

```python
"""
02_build_note_pool.py
Run from: scribe-iq/data_prep/

Builds unified indexed note pool from three sources:
  MedSynth  : HuggingFace Ahmad0067/MedSynth      (ICD-10 coded SOAP notes)
  MTSamples : HuggingFace harishnair04/mtsamples   (human-written progress notes)
  ACI-Bench : github.com/microsoft/clinical_visit_note_summarization_corpus

Output: data/staging/note_pool.jsonl
"""

from pathlib import Path
from datasets import load_dataset
import pandas as pd
from tqdm import tqdm
from utils.mappings import ICD10_TO_SPECIALTY, MTSAMPLES_TO_STANDARD_SPECIALTY
from utils.io_utils import write_jsonl, count_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT    = REPO_ROOT / "data/staging/note_pool.jsonl"
ACI_DIR   = REPO_ROOT / "data/raw/aci_bench"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.unlink(missing_ok=True)


def normalize_icd10(value) -> str:
    """Safely coerce ICD-10 field to string, handling None/list/float."""
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    try:
        return str(value).strip()
    except Exception:
        return ""


OUTPATIENT_KEYWORDS = [
    "progress note", "office visit", "office note", "soap",
    "follow-up", "followup", "follow up", "clinic note",
    "consult", "history and physical", "h&p", "outpatient",
    "checkup", "check-up", "annual", "wellness", "recheck",
]

EXCLUDED_SPECIALTIES = {
    "Surgery", "Neurosurgery", "Radiology", "Lab Medicine - Pathology",
    "Letters", "Discharge Summary", "Emergency Room Reports",
    "Autopsy", "IME-QME-Work Comp etc.", "Cosmetic / Plastic Surgery",
}


def is_outpatient_note(row) -> bool:
    if row.get("medical_specialty", "") in EXCLUDED_SPECIALTIES:
        return False
    text = f"{row.get('sample_name','')} {row.get('description','')}".lower()
    return any(kw in text for kw in OUTPATIENT_KEYWORDS)


# ─── MedSynth ──────────────────────────────────────────────────────────────────
print("\n[1/3] Loading MedSynth from HuggingFace...")
medsynth = load_dataset("Ahmad0067/MedSynth", split="train")

for idx, row in enumerate(tqdm(medsynth, desc="MedSynth")):
    icd10    = normalize_icd10(row.get("ICD10"))
    specialty = ICD10_TO_SPECIALTY.get(icd10[0] if icd10 else "X", "General Medicine")
    note_text = row.get("note") or ""
    dialogue  = row.get("dialogue") or ""

    if len(note_text) < 50:
        continue  # skip empty/stub notes

    write_jsonl(OUTPUT, {
        "note_id":        f"ms_{idx:06d}",
        "source":         "medsynth",
        "specialty":      specialty,
        "icd10_code":     icd10,
        "icd10_desc":     str(row.get("ICD10_desc") or ""),
        "note_type":      "soap",
        "note_text":      note_text,
        "dialogue":       dialogue if dialogue else None,
        "chief_complaint": None,
        "gender":         None,
        "word_count":     len(note_text.split()),
        "quality_tier":   "primary",
    })

print(f"  MedSynth done: {count_jsonl(OUTPUT)} records")


# ─── MTSamples ─────────────────────────────────────────────────────────────────
print("\n[2/3] Loading MTSamples from HuggingFace...")
mtsamples  = load_dataset("harishnair04/mtsamples", split="train")
mts_count  = 0

for idx, row in enumerate(tqdm(mtsamples, desc="MTSamples")):
    if not is_outpatient_note(row):
        continue
    transcription = row.get("transcription") or ""
    if len(transcription) < 100:
        continue

    raw_specialty = (row.get("medical_specialty") or "General Medicine").strip()
    specialty     = MTSAMPLES_TO_STANDARD_SPECIALTY.get(raw_specialty, raw_specialty)

    write_jsonl(OUTPUT, {
        "note_id":        f"mts_{idx:06d}",
        "source":         "mtsamples",
        "specialty":      specialty,
        "icd10_code":     None,
        "icd10_desc":     None,
        "note_type":      "progress_note",
        "note_text":      transcription,
        "dialogue":       None,
        "chief_complaint": row.get("description") or "",
        "gender":         None,
        "keywords":       row.get("keywords") or "",
        "word_count":     len(transcription.split()),
        "quality_tier":   "primary",
    })
    mts_count += 1

print(f"  MTSamples done: {mts_count} outpatient notes added")


# ─── ACI-Bench ─────────────────────────────────────────────────────────────────
print("\n[3/3] Loading ACI-Bench...")
if not ACI_DIR.exists():
    print("  WARNING: ACI-Bench not found.")
    print(f"  Clone to: {ACI_DIR}")
    print("  git clone https://github.com/microsoft/clinical_visit_note_summarization_corpus data/raw/aci_bench")
else:
    aci_count = 0
    # Walk all subsets: aci, virtassist, virtscribe
    for meta_file in sorted(ACI_DIR.rglob("*metadata*.csv")):
        try:
            meta_df = pd.read_csv(meta_file)
        except Exception as e:
            print(f"  Could not read {meta_file}: {e}")
            continue

        # Find matching src-tgt file in same directory
        src_tgt_candidates = list(meta_file.parent.glob("*src-tgt*.csv"))
        if not src_tgt_candidates:
            continue
        src_tgt_df = pd.read_csv(src_tgt_candidates[0])

        # Merge on encounter_id or id (whichever is present in both)
        merge_key = "encounter_id" if "encounter_id" in src_tgt_df.columns else "id"
        if merge_key not in meta_df.columns:
            continue

        merged = meta_df.merge(src_tgt_df, on=merge_key, how="inner")

        for _, row in merged.iterrows():
            note_text = str(row.get("note") or row.get("tgt") or "")
            dialogue  = str(row.get("src") or "")
            if len(note_text) < 50:
                continue

            write_jsonl(OUTPUT, {
                "note_id":        f"aci_{row[merge_key]}",
                "source":         "aci_bench",
                "specialty":      "General Medicine",  # classified in Script 03
                "icd10_code":     None,
                "icd10_desc":     None,
                "note_type":      "full_encounter",
                "note_text":      note_text,
                "dialogue":       dialogue if len(dialogue) > 20 else None,
                "chief_complaint": str(row.get("cc") or ""),
                "gender":         str(row.get("gender") or ""),
                "patient_name":   f"{row.get('patient_firstname','')} {row.get('patient_familyname','')}".strip(),
                "doctor_name":    str(row.get("doctor_name") or ""),
                "word_count":     len(note_text.split()),
                "quality_tier":   "primary",
            })
            aci_count += 1

    print(f"  ACI-Bench done: {aci_count} encounters added")


total = count_jsonl(OUTPUT)
print(f"\n✓ Note pool complete: {total} total notes → {OUTPUT}")
```

---

## Script 03 — Reserve ACI-Bench Encounters

**File:** `data_prep/scripts/03_reserve_aci_encounters.py`

> **Why this exists:** ACI-Bench is too small (~207 encounters) to leave its assignment
> to match luck. If ACI notes aren't reserved upfront, many showcase encounters
> get a MedSynth or MTSamples note instead. This script classifies ACI-Bench by
> specialty and pre-assigns one encounter per patient specialty slot.

```python
"""
03_reserve_aci_encounters.py
Run from: scribe-iq/data_prep/

Classifies ACI-Bench encounters by specialty using chief complaint.
Reserves one ACI encounter per target specialty for showcase assignment.
Output: data/staging/aci_reservations.jsonl
"""

from pathlib import Path
from collections import defaultdict
from utils.io_utils import load_jsonl, write_jsonl
from utils.mappings import ICD10_TO_SPECIALTY, CC_TO_SPECIALTY

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTE_POOL = REPO_ROOT / "data/staging/note_pool.jsonl"
OUTPUT    = REPO_ROOT / "data/staging/aci_reservations.jsonl"
OUTPUT.unlink(missing_ok=True)

# Target: one reserved ACI encounter per specialty
# Extra slots available for specialties with multiple ACI encounters
RESERVE_PER_SPECIALTY = 5  # reserve up to 5 per specialty

aci_notes = [
    n for n in load_jsonl(NOTE_POOL)
    if n["source"] == "aci_bench" and n.get("dialogue")
]

print(f"ACI-Bench encounters with dialogue: {len(aci_notes)}")

# Classify each by specialty using chief complaint
def classify_chief_complaint(cc: str) -> str:
    """Map chief complaint text to specialty using keyword rules."""
    if not cc:
        return "General Medicine"
    cc_lower = cc.lower()
    for keywords, specialty in CC_TO_SPECIALTY.items():
        if any(kw in cc_lower for kw in keywords):
            return specialty
    return "General Medicine"

specialty_buckets = defaultdict(list)
for note in aci_notes:
    specialty = classify_chief_complaint(note.get("chief_complaint", ""))
    note["specialty"] = specialty  # update in-memory
    specialty_buckets[specialty].append(note)

print("\nACI-Bench specialty distribution:")
for spec, notes in sorted(specialty_buckets.items(), key=lambda x: -len(x[1])):
    print(f"  {spec:<30} {len(notes)}")

# Reserve encounters — take up to RESERVE_PER_SPECIALTY per specialty
reserved = []
used_note_ids = set()
for specialty, notes in specialty_buckets.items():
    count = 0
    for note in notes:
        if count >= RESERVE_PER_SPECIALTY:
            break
        if note["note_id"] not in used_note_ids:
            write_jsonl(OUTPUT, {
                "note_id":        note["note_id"],
                "specialty":      specialty,
                "chief_complaint": note.get("chief_complaint", ""),
                "gender":         note.get("gender", ""),
                "note_text":      note["note_text"],
                "dialogue":       note["dialogue"],
                "reserved_for":   specialty,
            })
            used_note_ids.add(note["note_id"])
            count += 1

print(f"\n✓ Reserved {sum(1 for _ in load_jsonl(OUTPUT))} ACI encounters")
print(f"  Output: {OUTPUT}")
```

**Add to `utils/mappings.py`:**

```python
# Chief complaint keywords → specialty (for ACI-Bench classification)
# Keys are tuples of keywords, values are specialty strings
CC_TO_SPECIALTY = {
    ("chest", "cardiac", "heart", "palpitation", "angina", "hypertension"): "Cardiology",
    ("seizure", "neuro", "headache", "migraine", "stroke", "memory", "tremor"): "Neurology",
    ("knee", "hip", "back pain", "joint", "fracture", "orthop", "shoulder"): "Orthopedics",
    ("bowel", "abdominal", "crohn", "colitis", "gastro", "reflux", "diarrhea"): "Gastroenterology",
    ("breath", "asthma", "copd", "pulmon", "cough", "lung"): "Pulmonology",
    ("kidney", "renal", "dialysis", "ckd"): "Nephrology",
    ("skin", "rash", "dermat", "psoriasis", "eczema"): "Dermatology",
    ("diabetes", "thyroid", "endocrin", "glucose", "insulin"): "Endocrinology",
    ("depression", "anxiety", "psych", "bipolar", "mental"): "Psychiatry",
    ("urin", "prostate", "bladder", "urolag"): "Urology",
    ("eye", "vision", "ophthalm", "cataract", "glaucoma"): "Ophthalmology",
    ("ear", "nose", "throat", "ent", "sinus", "hearing"): "Otorhinolaryngology",
}
```

---

## Script 04 — Match and Score

**File:** `data_prep/scripts/04_match_and_score.py`

```python
"""
04_match_and_score.py
Run from: scribe-iq/data_prep/

Matches every Synthea patient/encounter to the best note in the pool.
ACI-Bench reserved encounters (from script 03) are excluded from the general
pool and only assigned in script 06 as showcase encounters.

Output: data/staging/match_results.jsonl
"""

from pathlib import Path
import pandas as pd
from tqdm import tqdm
from collections import defaultdict
from utils.mappings import SNOMED_TO_ICD10, ICD10_TO_SPECIALTY
from utils.io_utils import write_jsonl, load_jsonl
from utils.synthea_utils import load_synthea, get_active_conditions, get_active_medications

REPO_ROOT   = Path(__file__).resolve().parents[2]
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
NOTE_POOL   = REPO_ROOT / "data/staging/note_pool.jsonl"
ACI_RES     = REPO_ROOT / "data/staging/aci_reservations.jsonl"
OUTPUT      = REPO_ROOT / "data/staging/match_results.jsonl"
OUTPUT.unlink(missing_ok=True)

# Load reserved ACI IDs so they're excluded from general matching
reserved_aci_ids = {r["note_id"] for r in load_jsonl(ACI_RES)}
print(f"Reserved ACI encounters excluded from pool: {len(reserved_aci_ids)}")

# Load note pool (excluding reserved ACI)
all_notes = [
    n for n in load_jsonl(NOTE_POOL)
    if n["note_id"] not in reserved_aci_ids
]
print(f"Notes available for matching: {len(all_notes)}")

# ─── Index notes by specialty ─────────────────────────────────────────────────
# FIX: General Medicine index is a CAPPED SAMPLE, not the full pool
# This prevents O(n*m) blowup when falling back to General Medicine

GM_SAMPLE_SIZE = 200  # max General Medicine fallback candidates per query

notes_by_specialty = defaultdict(list)
gm_notes = []

for note in all_notes:
    spec = note["specialty"]
    notes_by_specialty[spec].append(note)
    if spec == "General Medicine":
        gm_notes.append(note)

# Shuffle for variety before capping
import random
random.seed(42)
random.shuffle(gm_notes)
gm_fallback = gm_notes[:GM_SAMPLE_SIZE]

print(f"\nNote pool by specialty:")
for spec, notes in sorted(notes_by_specialty.items(), key=lambda x: -len(x[1])):
    print(f"  {spec:<30} {len(notes)}")
print(f"  {'General Medicine fallback cap':<30} {GM_SAMPLE_SIZE}")


# ─── Scoring ──────────────────────────────────────────────────────────────────
def score_match(encounter: dict, note: dict) -> float:
    score = 0.0

    # 1. Specialty match (0.40)
    if note["specialty"] == encounter["specialty"]:
        score += 0.40
    elif note["specialty"] == "General Medicine":
        score += 0.08  # small partial credit only

    # 2. ICD-10 match (0.35) — exact 3-char prefix or chapter match
    note_icd    = (note.get("icd10_code") or "")
    enc_icd_list = encounter.get("icd10_codes", [])
    if note_icd and enc_icd_list:
        for enc_icd in enc_icd_list:
            if not enc_icd:
                continue
            if note_icd[:3] == enc_icd[:3]:      # e.g. I25 == I25
                score += 0.35
                break
            elif note_icd[0] == enc_icd[0]:       # e.g. I == I
                score += 0.12
                break

    # 3. Condition keyword overlap (0.15)
    conditions = encounter.get("conditions", [])
    note_text  = (note.get("note_text") or "").lower()
    if conditions:
        # Match on 5+ char words from condition names
        matched = sum(
            1 for cond in conditions
            if any(
                word in note_text
                for word in cond.lower().split()
                if len(word) >= 5
            )
        )
        score += 0.15 * (matched / len(conditions))

    # 4. Quality tier bonus (0.05)
    tier_weights = {"primary": 0.05, "secondary": 0.02, "fallback": 0.0}
    score += tier_weights.get(note.get("quality_tier", "fallback"), 0)

    # 5. Has dialogue (0.05 bonus)
    if note.get("dialogue"):
        score += 0.05

    return round(min(score, 1.0), 3)


# ─── Load Synthea ─────────────────────────────────────────────────────────────
print("\nLoading Synthea data...")
synthea       = load_synthea(SYNTHEA_DIR)
patients_df   = synthea["patients"]
encounters_df = synthea["encounters"]
conditions_df = synthea["conditions"]
meds_df       = synthea["medications"]
obs_df        = synthea["observations"]


# ─── Match all patients ───────────────────────────────────────────────────────
print(f"\nMatching {len(patients_df)} patients...")

for patient_id in tqdm(patients_df["Id"].unique()):
    pt_row = patients_df[patients_df["Id"] == patient_id].iloc[0]
    birth_date = pd.to_datetime(pt_row["BIRTHDATE"])
    gender = pt_row["GENDER"]

    pt_encounters = encounters_df[
        encounters_df["PATIENT"] == patient_id
    ].sort_values("START")

    if len(pt_encounters) < 3:
        continue

    for _, enc in pt_encounters.iterrows():
        enc_date = pd.to_datetime(enc["START"])
        age = int((enc_date - birth_date).days / 365.25)

        active_conditions = get_active_conditions(conditions_df, patient_id, enc_date)
        active_meds       = get_active_medications(meds_df, patient_id, enc_date)
        recent_obs        = obs_df[
            (obs_df["PATIENT"] == patient_id) &
            (pd.to_datetime(obs_df["DATE"]) <= enc_date)
        ].tail(10)

        icd10_codes = list(filter(None, [
            SNOMED_TO_ICD10.get(str(code))
            for code in active_conditions["CODE"].tolist()
        ]))

        specialty = ICD10_TO_SPECIALTY.get(
            icd10_codes[0][0] if icd10_codes else "X",
            "General Medicine"
        )

        enc_record = {
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

        # Candidate pool: specialty-specific + capped GM fallback
        candidates = notes_by_specialty.get(specialty, [])
        if specialty != "General Medicine":
            candidates = candidates + gm_fallback

        best_note  = None
        best_score = 0.0

        for note in candidates:
            s = score_match(enc_record, note)
            if s > best_score:
                best_score = s
                best_note  = note

        write_jsonl(OUTPUT, {
            **enc_record,
            "best_note_id":      best_note["note_id"] if best_note else None,
            "best_note_source":  best_note["source"] if best_note else None,
            "best_note_text":    best_note["note_text"] if best_note else None,
            "best_note_dialogue": best_note.get("dialogue") if best_note else None,
            "match_score":       best_score,
        })

print(f"\n✓ Matching complete → {OUTPUT}")
```

---

## Script 05 — Select Top 50

**File:** `data_prep/scripts/05_select_patients.py`

```python
"""
05_select_patients.py
Run from: scribe-iq/data_prep/

Selects top 50 patients by match quality with specialty distribution constraint.
Output: data/staging/selected_patients.jsonl
"""

from pathlib import Path
from collections import defaultdict, Counter
from utils.io_utils import load_jsonl, write_jsonl
from utils.mappings import ICD10_TO_SPECIALTY

REPO_ROOT     = Path(__file__).resolve().parents[2]
MATCH_RESULTS = REPO_ROOT / "data/staging/match_results.jsonl"
OUTPUT        = REPO_ROOT / "data/staging/selected_patients.jsonl"
OUTPUT.unlink(missing_ok=True)

TARGET_TOTAL        = 50
MAX_PER_SPECIALTY   = 6
MIN_ENCOUNTERS      = 3
MIN_AVG_MATCH_SCORE = 0.35

results = list(load_jsonl(MATCH_RESULTS))

patient_data = defaultdict(lambda: {
    "encounters": [], "scores": [], "specialties": []
})
for r in results:
    pid = r["patient_id"]
    patient_data[pid]["encounters"].append(r)
    patient_data[pid]["scores"].append(r["match_score"])
    patient_data[pid]["specialties"].append(r["specialty"])

scored_patients = []
for pid, data in patient_data.items():
    n_enc     = len(data["encounters"])
    avg_score = sum(data["scores"]) / len(data["scores"])

    if n_enc < MIN_ENCOUNTERS:
        continue
    if avg_score < MIN_AVG_MATCH_SCORE:
        continue
    if not any(r.get("conditions") for r in data["encounters"]):
        continue

    primary_specialty = Counter(data["specialties"]).most_common(1)[0][0]

    scored_patients.append({
        "patient_id":        pid,
        "quality_score":     round(avg_score, 3),
        "encounter_count":   n_enc,
        "primary_specialty": primary_specialty,
    })

scored_patients.sort(key=lambda x: x["quality_score"], reverse=True)

selected         = []
specialty_counts = defaultdict(int)

for patient in scored_patients:
    spec = patient["primary_specialty"]
    if specialty_counts[spec] >= MAX_PER_SPECIALTY:
        continue
    selected.append(patient)
    specialty_counts[spec] += 1
    if len(selected) >= TARGET_TOTAL:
        break

for p in selected:
    write_jsonl(OUTPUT, p)

print(f"\n✓ Selected {len(selected)} patients")
print(f"\nSpecialty distribution:")
for spec, count in sorted(specialty_counts.items(), key=lambda x: -x[1]):
    print(f"  {spec:<30} {count}")

scores = [p["quality_score"] for p in selected]
print(f"\nQuality score range: {min(scores):.3f} – {max(scores):.3f}")
print(f"Output: {OUTPUT}")
```

---

## Script 06 — Adapt Notes via Groq

**File:** `data_prep/scripts/06_adapt_notes.py`

```python
"""
06_adapt_notes.py
Run from: scribe-iq/data_prep/

Adapts matched notes to be coherent with each patient's Synthea record.
Assigns reserved ACI-Bench encounter as showcase for each patient.

Model: llama-3.1-70b-versatile  (verify current name at console.groq.com/docs)
       If deprecated, update MODEL constant before running.

Free tier: ~14,400 requests/day — 125 notes fits comfortably.
Set env var: export GROQ_API_KEY=gsk_...
Get free key: https://console.groq.com
"""

import os, time
from pathlib import Path
from collections import defaultdict
from groq import Groq
from utils.io_utils import load_jsonl, write_jsonl
from utils.synthea_utils import load_synthea, compute_age
from utils.note_checks import check_note_coherence

REPO_ROOT   = Path(__file__).resolve().parents[2]
SELECTED    = REPO_ROOT / "data/staging/selected_patients.jsonl"
MATCHES     = REPO_ROOT / "data/staging/match_results.jsonl"
ACI_RES     = REPO_ROOT / "data/staging/aci_reservations.jsonl"
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
OUTPUT      = REPO_ROOT / "data/staging/adapted_notes.jsonl"
OUTPUT.unlink(missing_ok=True)

# ── Check Groq model name at https://console.groq.com/docs/models ──────────────
MODEL = "llama-3.1-70b-versatile"
# ──────────────────────────────────────────────────────────────────────────────

client  = Groq(api_key=os.environ["GROQ_API_KEY"])
synthea = load_synthea(SYNTHEA_DIR)

# Index ACI reservations by specialty (pick best fit per patient)
aci_by_specialty = defaultdict(list)
for r in load_jsonl(ACI_RES):
    aci_by_specialty[r["specialty"]].append(r)

aci_used = set()  # track used ACI encounter IDs across patients

# Index match results
all_matches = list(load_jsonl(MATCHES))
by_patient  = defaultdict(list)
for m in all_matches:
    by_patient[m["patient_id"]].append(m)

selected   = list(load_jsonl(SELECTED))
patients_df = synthea["patients"]
note_idx    = 0

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


def call_groq(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=900,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1}: {e}")
                time.sleep(2 ** attempt)
            else:
                raise


def format_obs(obs_list: list) -> str:
    if not obs_list:
        return "None recorded"
    return "\n".join(
        f"- {o.get('DESCRIPTION','')}: {o.get('VALUE','')} {o.get('UNITS','')}".strip()
        for o in obs_list[:8]
    )


for patient in selected:
    pid   = patient["patient_id"]
    pt    = patients_df[patients_df["Id"] == pid].iloc[0]
    sex   = "Male" if pt["GENDER"] == "M" else "Female"
    spec  = patient["primary_specialty"]

    pt_matches = sorted(by_patient[pid], key=lambda x: x["encounter_date"])
    prior_visits  = pt_matches[:-1]
    current_visit = pt_matches[-1]

    print(f"\n{pid}  {spec}  {len(pt_matches)} encounters")

    # ── Prior visits: adapt reference note ────────────────────────────────────
    for enc in prior_visits:
        if not enc.get("best_note_text"):
            continue

        age    = compute_age(pt["BIRTHDATE"], enc["encounter_date"])
        prompt = ADAPT_PROMPT.format(
            age=age, sex=sex,
            visit_date=enc["encounter_date"][:10],
            visit_reason=enc.get("encounter_reason", "Follow-up visit"),
            conditions=", ".join(enc.get("conditions", [])) or "None documented",
            medications=", ".join(enc.get("medications", [])) or "None documented",
            observations=format_obs(enc.get("recent_obs", [])),
            reference_note=enc["best_note_text"][:2500],
        )

        print(f"  [{enc['encounter_date'][:10]}] adapting "
              f"({enc['best_note_source']}, score={enc['match_score']:.2f})...",
              end=" ", flush=True)

        adapted = call_groq(prompt)

        # Post-adaptation coherence check
        issues = check_note_coherence(
            adapted,
            enc.get("conditions", []),
            enc.get("medications", [])
        )
        if issues:
            print(f"⚠ {len(issues)} coherence warning(s): {issues[:2]}")
        else:
            print("ok")

        write_jsonl(OUTPUT, {
            "adapted_note_id":   f"note_{note_idx:06d}",
            "encounter_id":      enc["encounter_id"],
            "patient_id":        pid,
            "encounter_date":    enc["encounter_date"],
            "note_text":         adapted,
            "reference_note_id": enc["best_note_id"],
            "reference_source":  enc["best_note_source"],
            "match_score":       enc["match_score"],
            "coherence_issues":  issues,
            "is_showcase":       False,
            "has_dialogue":      False,
        })
        note_idx += 1

    # ── Current (showcase) visit: assign reserved ACI-Bench encounter ─────────
    aci_candidates = [
        r for r in aci_by_specialty.get(spec, [])
        if r["note_id"] not in aci_used
    ]
    # Also try General Medicine ACI as fallback
    if not aci_candidates:
        aci_candidates = [
            r for r in aci_by_specialty.get("General Medicine", [])
            if r["note_id"] not in aci_used
        ]

    if aci_candidates:
        # Pick best gender match if possible
        gender_match = [c for c in aci_candidates
                        if c.get("gender", "").upper() == pt["GENDER"].upper()]
        aci_enc = gender_match[0] if gender_match else aci_candidates[0]
        aci_used.add(aci_enc["note_id"])

        write_jsonl(OUTPUT, {
            "adapted_note_id":   f"note_{note_idx:06d}",
            "encounter_id":      current_visit["encounter_id"],
            "patient_id":        pid,
            "encounter_date":    current_visit["encounter_date"],
            "note_text":         aci_enc["note_text"],
            "dialogue":          aci_enc["dialogue"],
            "reference_note_id": aci_enc["note_id"],
            "reference_source":  "aci_bench",
            "match_score":       current_visit["match_score"],
            "coherence_issues":  [],
            "is_showcase":       True,
            "has_dialogue":      True,
        })
        print(f"  [{current_visit['encounter_date'][:10]}] showcase → ACI-Bench "
              f"({aci_enc['specialty']}, {aci_enc.get('gender','')})")
    else:
        # No ACI available: adapt the matched note, use MedSynth dialogue if present
        if current_visit.get("best_note_text"):
            age    = compute_age(pt["BIRTHDATE"], current_visit["encounter_date"])
            prompt = ADAPT_PROMPT.format(
                age=age, sex=sex,
                visit_date=current_visit["encounter_date"][:10],
                visit_reason=current_visit.get("encounter_reason", "Follow-up"),
                conditions=", ".join(current_visit.get("conditions", [])) or "None",
                medications=", ".join(current_visit.get("medications", [])) or "None",
                observations=format_obs(current_visit.get("recent_obs", [])),
                reference_note=current_visit["best_note_text"][:2500],
            )
            adapted  = call_groq(prompt)
            dialogue = current_visit.get("best_note_dialogue")

            write_jsonl(OUTPUT, {
                "adapted_note_id":  f"note_{note_idx:06d}",
                "encounter_id":     current_visit["encounter_id"],
                "patient_id":       pid,
                "encounter_date":   current_visit["encounter_date"],
                "note_text":        adapted,
                "dialogue":         dialogue,
                "reference_source": current_visit["best_note_source"],
                "match_score":      current_visit["match_score"],
                "coherence_issues": [],
                "is_showcase":      True,
                "has_dialogue":     bool(dialogue),
            })
            print(f"  [{current_visit['encounter_date'][:10]}] showcase → adapted "
                  f"(no ACI available, dialogue={'yes' if dialogue else 'no'})")
    note_idx += 1

print(f"\n✓ Adaptation complete: {note_idx} notes → {OUTPUT}")
```

---

## Script 07 — Assemble Corpus

*(Unchanged from v1 except updated path resolution using `Path(__file__).resolve().parents[2]`
for all paths. Apply this pattern to every `open()` and `pd.read_csv()` call.)*

Key change from v1 — path pattern:
```python
# Replace all hardcoded paths with:
REPO_ROOT   = Path(__file__).resolve().parents[2]
CORPUS_DIR  = REPO_ROOT / "data/clinical_corpus"
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
```

---

## Script 08 — Generate Dataset Card (NEW)

**File:** `data_prep/scripts/08_generate_dataset_card.py`

```python
"""
08_generate_dataset_card.py
Run from: scribe-iq/data_prep/

Generates dataset_card.md for the clinical corpus.
"""

from pathlib import Path
from collections import Counter
from utils.io_utils import load_jsonl
import json
from datetime import datetime

REPO_ROOT  = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data/clinical_corpus"

patients   = list(load_jsonl(CORPUS_DIR / "patients.jsonl"))
notes      = list(load_jsonl(CORPUS_DIR / "notes.jsonl"))
dialogues  = list(load_jsonl(CORPUS_DIR / "dialogues.jsonl"))
manifest   = json.loads((CORPUS_DIR / "manifest.json").read_text())

specialty_dist = Counter(p["primary_specialty"] for p in patients)
source_dist    = Counter(n["reference_source"] for n in notes)
showcase_count = sum(1 for n in notes if n.get("is_showcase"))
aci_dialogue   = sum(1 for d in dialogues if True)  # all dialogues

card = f"""# Scribe-IQ Clinical Corpus

**Version:** 1.0  
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d')}  
**Pipeline:** scribe-iq/data_prep/

---

## Summary

Synthetic clinical corpus of {len(patients)} patients designed for the Scribe-IQ
clinical AI demo. Each patient has a longitudinal encounter history with attached
clinical notes and one showcase encounter with a full doctor-patient dialogue.

The corpus is not intended for clinical use. It contains no real patient data.
All structured data is from Synthea (synthetic). Notes are either human-written
(MTSamples), synthetically generated (MedSynth), or expert-created (ACI-Bench),
adapted to each patient's specific Synthea record via LLM.

---

## Source Datasets

| Dataset | License | Role |
|---|---|---|
| Synthea v3 (seed=42) | Apache 2.0 | Patient spine — demographics, conditions, medications, labs, encounters |
| MTSamples | CC0 Public Domain | Human-written outpatient progress notes |
| MedSynth (Ahmad0067/MedSynth) | HuggingFace | ICD-10 coded SOAP dialogue-note pairs |
| ACI-Bench (microsoft/clinical_visit_note_summarization_corpus) | CC BY 4.0 | Expert-created full encounter dialogues |

---

## Corpus Statistics

| Entity | Count |
|---|---|
| Patients | {len(patients)} |
| Encounters | {manifest['record_counts'].get('encounters', 'N/A')} |
| Notes | {len(notes)} |
| Dialogues | {aci_dialogue} |
| Conditions | {manifest['record_counts'].get('conditions', 'N/A')} |
| Medications | {manifest['record_counts'].get('medications', 'N/A')} |

## Specialty Distribution

| Specialty | Patients |
|---|---|
{chr(10).join(f'| {s} | {c} |' for s, c in sorted(specialty_dist.items()))}

## Note Source Breakdown

| Source | Notes |
|---|---|
{chr(10).join(f'| {s} | {c} |' for s, c in sorted(source_dist.items()))}

---

## Known Limitations

- MTSamples notes are 10-15 years old; some medication names and practices may be outdated
- MedSynth notes are LLM-generated; clinical accuracy is not guaranteed
- ACI-Bench specialty coverage is narrow (primarily primary care and common outpatient)
- LLM adaptation (Groq / llama-3.1-70b-versatile) may introduce minor hallucinations; notes were spot-checked but not clinically validated
- SNOMED→ICD-10 mapping covers top ~40 Synthea conditions; rare conditions fall back to specialty-only matching
- Corpus should not be used for clinical decision support, clinical training, or any real patient care

---

## Intended Use

- Demonstrating Scribe-IQ pre-meeting summary, note generation, and transcription features
- Portfolio demonstration of clinical data pipeline design
- Research and development of clinical NLP systems in a synthetic data environment

---

## Reproduction

```bash
cd scribe-iq/data_prep
bash scripts/01_generate_patients.sh
python scripts/02_build_note_pool.py
python scripts/03_reserve_aci_encounters.py
python scripts/04_match_and_score.py
python scripts/05_select_patients.py
python scripts/06_adapt_notes.py
python scripts/07_assemble_corpus.py
python scripts/08_generate_dataset_card.py
python scripts/09_validate_corpus.py
```
"""

(CORPUS_DIR / "dataset_card.md").write_text(card)
print(f"✓ dataset_card.md written to {CORPUS_DIR}")
```

---

## `utils/note_checks.py` (NEW)

Post-adaptation coherence check — flags obvious hallucinations.

```python
"""
utils/note_checks.py

Checks adapted notes for coherence with the patient's Synthea record.
Returns a list of issue strings (empty list = no issues found).
"""


def check_note_coherence(
    note_text: str,
    expected_conditions: list,
    expected_medications: list,
) -> list:
    """
    Checks for two types of issues:
    1. Medication mentioned in note that is NOT in the patient's active med list
    2. Note is suspiciously short (may indicate adaptation failure)

    Returns list of warning strings. Empty list = clean.
    """
    issues = []
    note_lower = note_text.lower()

    # Check note length
    if len(note_text.split()) < 50:
        issues.append(f"Note is very short ({len(note_text.split())} words) — possible adaptation failure")

    # Build allowlist from expected medications
    # Extract significant tokens (5+ chars) from medication names
    allowed_med_tokens = set()
    for med in expected_medications:
        for token in med.lower().split():
            if len(token) >= 5:
                allowed_med_tokens.add(token)

    # Spot-check for common drug name patterns NOT in allowlist
    # This is a heuristic, not exhaustive
    COMMON_DRUG_SUFFIXES = [
        "olol", "pril", "sartan", "statin", "mycin",
        "cillin", "azole", "prazole", "tidine", "dipine",
    ]
    for suffix in COMMON_DRUG_SUFFIXES:
        import re
        pattern = rf"\b\w+{suffix}\b"
        matches = re.findall(pattern, note_lower)
        for match in matches:
            if match not in allowed_med_tokens and len(match) >= 7:
                issues.append(f"Possible unlisted medication in note: '{match}'")
                break  # one warning per suffix type is enough

    return issues
```

---

## Script 09 — Validate Corpus

**File:** `data_prep/scripts/09_validate_corpus.py`

Key fix from v1: precise showcase/dialogue count labeling.

```python
"""
09_validate_corpus.py — corrected version
"""

from pathlib import Path
from collections import defaultdict, Counter
import json
from utils.io_utils import load_jsonl

REPO_ROOT  = Path(__file__).resolve().parents[2]
CORPUS     = REPO_ROOT / "data/clinical_corpus"

patients   = list(load_jsonl(CORPUS / "patients.jsonl"))
encounters = list(load_jsonl(CORPUS / "encounters.jsonl"))
notes      = list(load_jsonl(CORPUS / "notes.jsonl"))
dialogues  = list(load_jsonl(CORPUS / "dialogues.jsonl"))
conditions = list(load_jsonl(CORPUS / "conditions.jsonl"))
medications= list(load_jsonl(CORPUS / "medications.jsonl"))

patient_ids   = {p["patient_id"] for p in patients}
encounter_ids = {e["encounter_id"] for e in encounters}
issues   = []
warnings = []

# Referential integrity
for e in encounters:
    if e["patient_id"] not in patient_ids:
        issues.append(f"Encounter {e['encounter_id']} has orphaned patient_id")
for n in notes:
    if n["encounter_id"] not in encounter_ids:
        issues.append(f"Note {n['note_id']} has orphaned encounter_id")
    if not n.get("note_text") or len(n["note_text"].split()) < 30:
        issues.append(f"Note {n['note_id']} is empty or too short")
for d in dialogues:
    if d["encounter_id"] not in encounter_ids:
        issues.append(f"Dialogue {d['dialogue_id']} has orphaned encounter_id")

# Showcase / dialogue counts — PRECISE labeling (v1 fix)
showcase_enc_ids    = {e["encounter_id"] for e in encounters if e.get("is_showcase")}
showcase_note_ids   = {n["encounter_id"] for n in notes if n.get("is_showcase")}
dialogue_enc_ids    = {d["encounter_id"] for d in dialogues}
aci_dialogue_ids    = {d["encounter_id"] for d in dialogues
                       if "aci" in d.get("source", "")}
showcase_with_dlg   = showcase_enc_ids & dialogue_enc_ids
showcase_aci_dlg    = showcase_enc_ids & aci_dialogue_ids
showcase_no_dlg     = showcase_enc_ids - dialogue_enc_ids

for enc_id in showcase_no_dlg:
    warnings.append(f"Showcase encounter {enc_id} has no dialogue attached")

# Stats
specialty_dist = Counter(p["primary_specialty"] for p in patients)
source_dist    = Counter(n["reference_source"] for n in notes)
score_vals     = [e["match_score"] for e in encounters]
avg_score      = sum(score_vals) / len(score_vals)

print(f"{'='*55}")
print(f"CORPUS AUDIT")
print(f"{'='*55}")
print(f"\nSCALE")
print(f"  Patients:             {len(patients)}")
print(f"  Encounters:           {len(encounters)}")
print(f"  Notes:                {len(notes)}")
print(f"  Dialogues (total):    {len(dialogues)}")
print(f"  Conditions:           {len(conditions)}")
print(f"  Medications:          {len(medications)}")

print(f"\nSHOWCASE ENCOUNTERS")
print(f"  Total showcase:                {len(showcase_enc_ids)}")
print(f"  Showcase with ANY dialogue:    {len(showcase_with_dlg)}")
print(f"  Showcase with ACI dialogue:    {len(showcase_aci_dlg)}")
print(f"  Showcase with NO dialogue:     {len(showcase_no_dlg)}")

print(f"\nSPECIALTY DISTRIBUTION")
for spec, count in sorted(specialty_dist.items(), key=lambda x: -x[1]):
    print(f"  {spec:<30} {count}")

print(f"\nNOTE SOURCE BREAKDOWN")
for source, count in sorted(source_dist.items(), key=lambda x: -x[1]):
    print(f"  {source:<20} {count}")

print(f"\nMATCH QUALITY")
print(f"  Average: {avg_score:.3f}"
      f"  Min: {min(score_vals):.3f}"
      f"  Max: {max(score_vals):.3f}")

print(f"\n{'ISSUES' if issues else 'ISSUES: none'}")
for issue in issues:
    print(f"  ✗ {issue}")

print(f"\n{'WARNINGS' if warnings else 'WARNINGS: none'}")
for w in warnings:
    print(f"  ⚠ {w}")

# Write audit report
report_lines = [
    "# Scribe-IQ Corpus Audit Report\n",
    f"## Scale\n| Patients | {len(patients)} |\n"
    f"| Encounters | {len(encounters)} |\n"
    f"| Notes | {len(notes)} |\n"
    f"| Dialogues | {len(dialogues)} |\n",
    f"## Showcase\n"
    f"| Total showcase | {len(showcase_enc_ids)} |\n"
    f"| With ACI dialogue | {len(showcase_aci_dlg)} |\n"
    f"| With any dialogue | {len(showcase_with_dlg)} |\n"
    f"| No dialogue | {len(showcase_no_dlg)} |\n",
    "## Issues\n" + ("None\n" if not issues else
                     "\n".join(f"- {i}" for i in issues) + "\n"),
    "## Warnings\n" + ("None\n" if not warnings else
                       "\n".join(f"- {w}" for w in warnings) + "\n"),
]
(CORPUS / "audit_report.md").write_text("\n".join(report_lines))
print(f"\n✓ audit_report.md written to {CORPUS}/")
```

---

## `utils/mappings.py` (corrected)

Duplicate SNOMED key `44054006` removed. Both entries were E11.x — kept the more
specific one (`E11.9`). Added `CC_TO_SPECIALTY` for ACI-Bench classification.

```python
# ── SNOMED CT → ICD-10-CM (top Synthea conditions) ────────────────────────────
# Source: NLM SNOMED CT to ICD-10-CM Map (simplified lookup for top 50 codes)
# Full map: https://www.nlm.nih.gov/research/umls/mapping_projects/snomedct_to_icd10cm.html
SNOMED_TO_ICD10 = {
    # Endocrine
    "44054006":  "E11.9",   # Type 2 diabetes mellitus (kept, removed duplicate)
    "46635009":  "E10.9",   # Type 1 diabetes
    "73595000":  "E03.9",   # Hypothyroidism
    "55822004":  "E78.5",   # Hyperlipidemia
    "162864005": "E66.9",   # Obesity
    "237599002": "E66.01",  # Morbid obesity
    # Cardiovascular
    "38341003":  "I10",     # Essential hypertension
    "59621000":  "I10",     # Hypertension NOS
    "53741008":  "I25.10",  # CAD, unspecified
    "49436004":  "I48.91",  # Atrial fibrillation
    "230690007": "I63.9",   # Cerebral infarction
    # Respiratory
    "195967001": "J45.909", # Asthma
    "267102003": "J45.20",  # Mild intermittent asthma
    "703151001": "J45.51",  # Moderate persistent asthma
    "13645005":  "J44.1",   # COPD exacerbation
    "233604007": "J15.9",   # Pneumonia
    "444814009": "J06.9",   # Viral URI
    "40122008":  "J18.9",   # Pneumonia NOS
    "36971009":  "J32.9",   # Sinusitis
    "43878008":  "J02.9",   # Strep pharyngitis
    # GI
    "34000006":  "K50.90",  # Crohn's disease
    "15777000":  "K21.0",   # GERD with esophagitis
    "74400008":  "K37",     # Appendicitis
    # Musculoskeletal
    "64859006":  "M81.0",   # Osteoporosis
    "396275006": "M19.90",  # Osteoarthritis
    "69896004":  "M06.9",   # Rheumatoid arthritis
    "370143000": "M54.5",   # Low back pain
    # Renal / Urology
    "40055000":  "N18.3",   # CKD stage 3
    "90688005":  "N18.9",   # CKD NOS
    "9855000":   "N40.1",   # BPH
    "57870002":  "N39.0",   # UTI
    "11840006":  "N20.0",   # Kidney stone
    "62106007":  "N10",     # Acute pyelonephritis
    # Neurological
    "84757009":  "G40.909", # Epilepsy
    "26929004":  "G30.9",   # Alzheimer's
    # Psychiatric
    "35489007":  "F32.9",   # Major depressive disorder
    "197480006": "F41.1",   # Generalized anxiety
    # Dermatology
    "415068001": "L40.0",   # Psoriasis
    # Haematology / Oncology
    "271737000": "D64.9",   # Anaemia
    "93761005":  "C18.9",   # Colorectal cancer
    "363346000": "C80.1",   # Malignant neoplasm unspecified
    # Other
    "195662009": "J06.9",   # Acute URI
    "3928004":   "H66.90",  # Otitis media
    "50043002":  "J96.00",  # Respiratory failure
    "298705000": "M79.3",   # Panniculitis
}

# ── ICD-10 first character → clinical specialty ────────────────────────────────
ICD10_TO_SPECIALTY = {
    "A": "Infectious Disease",
    "B": "Infectious Disease",
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

# ── MTSamples specialty → standard specialty name ─────────────────────────────
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
    "SOAP / Chart / Progress Notes": "General Medicine",
    "Office Notes":               "General Medicine",
    "Consult - History and Phy.": "General Medicine",
    "Pain Management":            "Orthopedics",
    "Sleep Medicine":             "Pulmonology",
    "Physical Medicine - Rehab":  "Orthopedics",
    "Podiatry":                   "Orthopedics",
    "Allergy / Immunology":       "Infectious Disease",
    "Chiropractic":               "Orthopedics",
}

# ── Chief complaint keywords → specialty (for ACI-Bench classification) ────────
# Keys are tuples of keywords, values are specialty strings
CC_TO_SPECIALTY = {
    ("chest", "cardiac", "heart", "palpitation", "angina", "coronary",
     "hypertension", "blood pressure"): "Cardiology",
    ("seizure", "neuro", "headache", "migraine", "stroke", "memory",
     "tremor", "epilepsy", "dizziness"): "Neurology",
    ("knee", "hip", "back pain", "joint", "fracture", "orthop",
     "shoulder", "bone", "arthritis", "spine"): "Orthopedics",
    ("bowel", "abdominal", "crohn", "colitis", "gastro", "reflux",
     "diarrhea", "stomach", "colon"): "Gastroenterology",
    ("breath", "asthma", "copd", "pulmon", "cough", "lung",
     "respiratory", "wheez"): "Pulmonology",
    ("kidney", "renal", "dialysis", "ckd", "creatinine"): "Nephrology",
    ("skin", "rash", "dermat", "psoriasis", "eczema", "acne"): "Dermatology",
    ("diabetes", "thyroid", "endocrin", "glucose", "insulin",
     "A1c", "weight"): "Endocrinology",
    ("depression", "anxiety", "psych", "bipolar", "mental",
     "mood", "panic"): "Psychiatry",
    ("urin", "prostate", "bladder", "urolog", "incontinence"): "Urology",
    ("eye", "vision", "ophthalm", "cataract", "glaucoma"): "Ophthalmology",
    ("ear", "nose", "throat", "ent", "sinus", "hearing",
     "tonsil"): "Otorhinolaryngology",
}
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

## README

```markdown
# Scribe-IQ Data Pipeline

Generates a synthetic clinical corpus of 50 patients for the Scribe-IQ demo.

## Prerequisites

- Python 3.11+
- Java 11+ (for Synthea)
- Groq API key (free at https://console.groq.com)

## Setup

```bash
# From repo root
pip install -r data_prep/requirements.txt

# Download Synthea JAR to repo root
curl -L https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar \
     -o synthea-with-dependencies.jar

# Clone ACI-Bench
git clone https://github.com/microsoft/clinical_visit_note_summarization_corpus \
          data/raw/aci_bench

# Set Groq key
export GROQ_API_KEY=gsk_...

# Set Python path
export PYTHONPATH="$(pwd)/data_prep:$PYTHONPATH"
```

## Run Pipeline

```bash
cd data_prep   # ALL scripts run from here

bash scripts/01_generate_patients.sh
python scripts/02_build_note_pool.py
python scripts/03_reserve_aci_encounters.py
python scripts/04_match_and_score.py
python scripts/05_select_patients.py
python scripts/06_adapt_notes.py
python scripts/07_assemble_corpus.py
python scripts/08_generate_dataset_card.py
python scripts/09_validate_corpus.py
```

## Resumability

Each script reads from the previous script's output.
If a script fails, fix the issue and re-run only that script.
Scripts 01-05 are idempotent (safe to re-run, they overwrite output).

## Estimated Runtime

| Script | Runtime |
|---|---|
| 01 generate patients | ~5 min |
| 02 build note pool | ~20 min |
| 03 reserve ACI | seconds |
| 04 match and score | ~45 min (M1 Max) |
| 05 select patients | seconds |
| 06 adapt notes | ~25 min (Groq) |
| 07 assemble corpus | ~5 min |
| 08 dataset card | seconds |
| 09 validate | seconds |
| **Total** | **~2 hours** |

## Relation to lakehouse-era proposals

**Historical proposals** sometimes assumed a **`lakehouse/`** script tree alongside demos; **this repository** executes corpus work only under **`data_prep/`**. Written lineage and diagrams live under **`reference-docs/CLINICAL_LAKEHOUSE_PROPOSAL_V2.md`** and **`docs/history/EVOLUTION.md`**.

Do not recreate a competing **`lakehouse/scripts`** tree for new work.

---

## Instructions for the Coding Agent

Paste this document as a project brief. Then:

1. **"Create the full directory structure"**
2. **"Implement utils/mappings.py, utils/io_utils.py, utils/synthea_utils.py, utils/note_checks.py"**
3. **"Implement scripts/01 through 09 one at a time, confirm each compiles before continuing"**
4. **"Run script 01 and show me the CSV output file list"**
5. Continue sequentially — do not skip ahead until each script runs successfully

Each script is independent and debuggable in isolation.
The pipeline is fully resumable — fix and rerun any single script without rerunning earlier steps.
