> **Archived (2026-05-05).** Superseded by **`docs/archive/SCRIBE_IQ_IMPLEMENTATION_CORRECTED.md`** and **`docs/reference/corpus_offline_pipeline_v2_brief.md`**. Kept for history only.

---

# Scribe-IQ — Simplified Implementation for 19 Golden Patients
## Implementation Plan (No Over-Engineering Edition)

---

## What Changed From Original Design

### REMOVED (over-engineering for 19 patients):
- ❌ Schema versioning (`context_schema_version`)
- ❌ Fingerprinting (`prior_context_fingerprint`)
- ❌ Per-row model metadata (use one model for entire run)
- ❌ Optional LLM micro-summaries (just use structured context)
- ❌ Deterministic rollup logic (union/set-diff)
- ❌ Frozen bundle tracking (commit SHAs)
- ❌ Configurable K via env vars (hardcode K=3)
- ❌ Resume capability (run once, works, done)
- ❌ Dental filtering flags

### KEPT (essentials):
- ✅ Longitudinal context extraction (K=3 prior visits)
- ✅ Prior visit structured blocks (dates, conditions, meds, obs)
- ✅ Adaptation with longitudinal context in prompt
- ✅ ACI-Bench showcase dialogues for 19 patients
- ✅ Basic provenance (source, is_showcase, has_dialogue)

---

## Repository Structure

```
scribe-iq/
  data_prep/
    scripts/
      05_select_patients.py          # existing
      05.5_extract_longitudinal_context.py  # NEW - simple version
      06_adapt_notes.py              # MODIFIED - with prior context
      06.5_match_aci_to_golden.py    # NEW - showcase dialogues
      07_assemble_corpus.py          # existing
      08_generate_dataset_card.py    # existing
      09_validate_corpus.py          # existing
    utils/
      __init__.py
      mappings.py
      io_utils.py
      synthea_utils.py
  data/
    staging/
      selected_patients_golden.jsonl          # 19 patients (EXISTS)
      match_results.jsonl                     # 269 encounters (EXISTS)
      patient_longitudinal_context.jsonl      # NEW - output of 05.5
      aci_showcase_dialogues.jsonl            # NEW - output of 06.5
      adapted_notes.jsonl                     # MODIFIED - output of 06
    clinical_corpus/
      # final outputs from 07
```

---

## Script 05.5 — Extract Longitudinal Context (NEW, Simplified)

**File:** `data_prep/scripts/05.5_extract_longitudinal_context.py`

**Purpose:** Build prior visit context (K=3 most recent prior encounters) for each golden patient encounter.

```python
"""
05.5_extract_longitudinal_context.py

Extracts longitudinal context for each golden patient encounter.
For encounter at time T, includes K=3 most recent prior visits.

Simple version:
- No schema versioning
- No fingerprinting
- Just the data needed for adaptation
"""

from pathlib import Path
import json
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN    = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
MATCHES   = REPO_ROOT / "data/staging/match_results.jsonl"
OUTPUT    = REPO_ROOT / "data/staging/patient_longitudinal_context.jsonl"

K_PRIOR_VISITS = 3  # how many prior visits to include

print("="*60)
print("EXTRACTING LONGITUDINAL CONTEXT")
print("="*60)

# Load golden patient IDs
golden_ids = {
    json.loads(line)["patient_id"]
    for line in open(GOLDEN)
}
print(f"\nGolden patients: {len(golden_ids)}")

# Load all matches for golden patients
matches = [
    json.loads(line) 
    for line in open(MATCHES)
    if json.loads(line)["patient_id"] in golden_ids
]
print(f"Total encounters for golden patients: {len(matches)}")

# Group by patient
by_patient = defaultdict(list)
for m in matches:
    by_patient[m["patient_id"]].append(m)

# Build longitudinal context
OUTPUT.unlink(missing_ok=True)
total_contexts = 0

for pid in golden_ids:
    encs = by_patient[pid]
    
    # Sort chronologically
    encs_sorted = sorted(encs, key=lambda x: x["encounter_date"])
    
    for i, current_enc in enumerate(encs_sorted):
        # Get K=3 prior visits (or fewer if at start of timeline)
        prior_start = max(0, i - K_PRIOR_VISITS)
        prior_encs = encs_sorted[prior_start:i]
        
        # Build prior visit blocks (structured data only)
        prior_blocks = []
        for prior in prior_encs:
            # Cap lists to keep context manageable
            conditions = prior.get("conditions", [])[:5]
            medications = prior.get("medications", [])[:5]
            obs = prior.get("recent_obs", [])[:3]
            
            prior_blocks.append({
                "date": prior["encounter_date"][:10],
                "reason": prior.get("encounter_reason", "Not documented"),
                "conditions": conditions,
                "medications": medications,
                "key_observations": [
                    f"{o.get('DESCRIPTION', 'Unknown')}: {o.get('VALUE', '')} {o.get('UNITS', '')}".strip()
                    for o in obs
                ],
            })
        
        # Write context record
        with open(OUTPUT, "a") as f:
            f.write(json.dumps({
                "patient_id": pid,
                "encounter_id": current_enc["encounter_id"],
                "encounter_date": current_enc["encounter_date"],
                "prior_visits": prior_blocks,
                "num_prior_visits": len(prior_blocks),
            }) + "\n")
        
        total_contexts += 1

print(f"\n✓ Longitudinal context extracted")
print(f"  Total context records: {total_contexts}")
print(f"  Output: {OUTPUT}")
print(f"\nContext structure:")
print(f"  - K={K_PRIOR_VISITS} most recent prior visits per encounter")
print(f"  - Structured blocks: date, reason, conditions, meds, obs")
print(f"  - Lists capped at: conditions=5, meds=5, obs=3")
```

**Expected Output:**
- `patient_longitudinal_context.jsonl` with 269 records (one per encounter)
- Each record has 0-3 prior visit blocks depending on position in timeline

---

## Script 06 — Adapt Notes With Longitudinal Context (MODIFIED)

**File:** `data_prep/scripts/06_adapt_notes.py`

**Changes from original:**
- Reads `patient_longitudinal_context.jsonl`
- Includes prior visit context in prompt
- Simplified output schema (no versioning/fingerprinting)
- Single model for all notes

```python
"""
06_adapt_notes.py

Adapts matched notes to be coherent with each patient's Synthea record.
Uses longitudinal context (K=3 prior visits) to generate notes that
reference patient history naturally.

Simplified for 19 golden patients:
- No schema versioning
- No fingerprinting
- One model for all notes
- Basic provenance only
"""

import os
import json
import time
from pathlib import Path
from collections import defaultdict
import pandas as pd
from groq import Groq
from utils.synthea_utils import compute_age

REPO_ROOT   = Path(__file__).resolve().parents[2]
GOLDEN      = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
MATCHES     = REPO_ROOT / "data/staging/match_results.jsonl"
CONTEXT     = REPO_ROOT / "data/staging/patient_longitudinal_context.jsonl"
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
OUTPUT      = REPO_ROOT / "data/staging/adapted_notes.jsonl"

# Groq model - check console.groq.com/docs/models for current model names
MODEL = "llama-3.1-70b-versatile"
client = Groq(api_key=os.environ["GROQ_API_KEY"])

print("="*60)
print("ADAPTING NOTES WITH LONGITUDINAL CONTEXT")
print("="*60)
print(f"Model: {MODEL}")

# Load longitudinal context lookup
context_lookup = {
    (json.loads(line)["patient_id"], json.loads(line)["encounter_id"]): json.loads(line)
    for line in open(CONTEXT)
}
print(f"\nLoaded context for {len(context_lookup)} encounters")

# Load golden patient IDs
golden_ids = {json.loads(line)["patient_id"] for line in open(GOLDEN)}

# Load matches for golden patients
matches = [
    json.loads(line) for line in open(MATCHES)
    if json.loads(line)["patient_id"] in golden_ids
]
print(f"Encounters to process: {len(matches)}")

# Group by patient
by_patient = defaultdict(list)
for m in matches:
    by_patient[m["patient_id"]].append(m)

# Load Synthea patients
patients_df = pd.read_csv(SYNTHEA_DIR / "patients.csv")

# Adaptation prompt template
ADAPT_PROMPT = """\
You are a clinical documentation specialist.

PATIENT HISTORY (prior visits):
{prior_context}

TODAY'S VISIT:
- Date: {visit_date}
- Patient: {age}-year-old {sex}
- Visit reason: {visit_reason}
- Active conditions: {conditions}
- Current medications: {medications}
- Recent vitals/labs:
{observations}

REFERENCE NOTE (use this structure and clinical writing style):
{reference_note}

Instructions:
1. Write a clinical note for TODAY'S VISIT using the reference note's structure
2. Reference relevant information from prior visits naturally where appropriate
3. Only include conditions and medications listed above for today
4. Do not invent lab values or procedures not mentioned
5. Keep the same professional tone and section format as the reference
6. Do not include patient names or identifiers

Write the adapted note now:"""


def format_prior_context(prior_blocks):
    """Format prior visit blocks into readable text for the prompt."""
    if not prior_blocks:
        return "No prior visits in recent history."
    
    lines = []
    for i, visit in enumerate(prior_blocks, 1):
        lines.append(f"\nVisit {i} ({visit['date']}):")
        lines.append(f"  Reason: {visit['reason']}")
        
        if visit.get('conditions'):
            lines.append(f"  Conditions: {', '.join(visit['conditions'])}")
        
        if visit.get('medications'):
            lines.append(f"  Medications: {', '.join(visit['medications'])}")
        
        if visit.get('key_observations'):
            obs_text = '; '.join(visit['key_observations'])
            lines.append(f"  Key findings: {obs_text}")
    
    return '\n'.join(lines)


def format_observations(obs_list):
    """Format observation list for the prompt."""
    if not obs_list:
        return "  None recorded"
    
    lines = []
    for o in obs_list[:5]:  # cap at 5
        desc = o.get('DESCRIPTION', 'Unknown')
        val = o.get('VALUE', '')
        units = o.get('UNITS', '')
        lines.append(f"  - {desc}: {val} {units}".strip())
    
    return '\n'.join(lines) if lines else "  None recorded"


def call_groq(prompt, retries=3):
    """Call Groq API with retry logic."""
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=900,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1}: {e}")
                time.sleep(2 ** attempt)
            else:
                raise


# Process all golden patients
OUTPUT.unlink(missing_ok=True)
note_idx = 0
total_prior_notes = 0
total_showcase = 0

for pid in sorted(golden_ids):
    pt_row = patients_df[patients_df["Id"] == pid].iloc[0]
    sex = "Male" if pt_row["GENDER"] == "M" else "Female"
    
    # Get encounters sorted chronologically
    encs = sorted(by_patient[pid], key=lambda x: x["encounter_date"])
    
    # All but last = prior visits to adapt
    # Last = showcase (will be handled separately with dialogue)
    prior_visits = encs[:-1]
    showcase = encs[-1]
    
    print(f"\n{pid} — {len(encs)} encounters ({len(prior_visits)} prior + 1 showcase)")
    
    # ── Adapt prior visits ────────────────────────────────────────────────
    for enc in prior_visits:
        if not enc.get("best_note_text"):
            print(f"  [{enc['encounter_date'][:10]}] no reference note, skipping")
            continue
        
        # Get longitudinal context for this encounter
        ctx = context_lookup.get((pid, enc["encounter_id"]))
        if not ctx:
            print(f"  [{enc['encounter_date'][:10]}] no context found, skipping")
            continue
        
        # Compute patient age at this encounter
        age = compute_age(pt_row["BIRTHDATE"], enc["encounter_date"])
        
        # Build prompt
        prompt = ADAPT_PROMPT.format(
            prior_context=format_prior_context(ctx["prior_visits"]),
            visit_date=enc["encounter_date"][:10],
            age=age,
            sex=sex,
            visit_reason=enc.get("encounter_reason", "Follow-up visit"),
            conditions=", ".join(enc.get("conditions", [])) or "None documented",
            medications=", ".join(enc.get("medications", [])) or "None documented",
            observations=format_observations(enc.get("recent_obs", [])),
            reference_note=enc["best_note_text"][:2500],  # cap reference length
        )
        
        print(f"  [{enc['encounter_date'][:10]}] adapting "
              f"({enc['best_note_source']}, score={enc['match_score']:.2f}, "
              f"{ctx['num_prior_visits']} prior)...", end=" ", flush=True)
        
        # Generate adapted note
        try:
            adapted_text = call_groq(prompt)
            
            # Write adapted note
            with open(OUTPUT, "a") as f:
                f.write(json.dumps({
                    "note_id": f"note_{note_idx:06d}",
                    "encounter_id": enc["encounter_id"],
                    "patient_id": pid,
                    "encounter_date": enc["encounter_date"],
                    "note_text": adapted_text,
                    "reference_source": enc["best_note_source"],
                    "reference_note_id": enc.get("best_note_id"),
                    "match_score": enc["match_score"],
                    "num_prior_visits_in_context": ctx["num_prior_visits"],
                    "adaptation_model": MODEL,
                    "is_showcase": False,
                    "has_dialogue": False,
                }) + "\n")
            
            note_idx += 1
            total_prior_notes += 1
            print("✓")
            
        except Exception as e:
            print(f"✗ Error: {e}")
        
        time.sleep(0.5)  # rate limit courtesy
    
    # ── Showcase encounter (will be assigned dialogue in next script) ────
    print(f"  [{showcase['encounter_date'][:10]}] showcase encounter "
          f"(dialogue assignment in script 06.5)")
    
    # For now, just note that this is a showcase
    # Script 06.5 will add the dialogue and final note
    total_showcase += 1

print(f"\n{'='*60}")
print(f"ADAPTATION COMPLETE")
print(f"{'='*60}")
print(f"Prior visit notes adapted: {total_prior_notes}")
print(f"Showcase encounters (pending dialogue): {total_showcase}")
print(f"Total notes written: {note_idx}")
print(f"Output: {OUTPUT}")
print(f"\nNext step: Run script 06.5 to assign ACI-Bench dialogues to showcases")
```

---

## Script 06.5 — Match ACI-Bench to Golden Showcases (NEW)

**File:** `data_prep/scripts/06.5_match_aci_to_golden.py`

**Purpose:** Assign best ACI-Bench dialogues to the 19 showcase encounters (one per patient).

```python
"""
06.5_match_aci_to_golden.py

Matches ACI-Bench encounters to golden patients for showcase demonstrations.
Assigns the best dialogue to each patient's last encounter.

Matching criteria (in priority order):
1. Specialty + Gender match
2. Specialty match only
3. General Medicine fallback

Also generates 2-3 additional examples by adapting MedSynth dialogues
for patients that don't get ACI-Bench matches.
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter

REPO_ROOT   = Path(__file__).resolve().parents[2]
GOLDEN      = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
MATCHES     = REPO_ROOT / "data/staging/match_results.jsonl"
ACI_DIR     = REPO_ROOT / "data/raw/aci_bench"
SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
OUTPUT      = REPO_ROOT / "data/staging/aci_showcase_dialogues.jsonl"

print("="*60)
print("MATCHING ACI-BENCH TO GOLDEN SHOWCASES")
print("="*60)

# ── Load ACI-Bench encounters ─────────────────────────────────────────────
print("\nLoading ACI-Bench...")
aci_encounters = []

if not ACI_DIR.exists():
    print(f"  ERROR: ACI-Bench not found at {ACI_DIR}")
    print(f"  Clone: git clone https://github.com/microsoft/clinical_visit_note_summarization_corpus {ACI_DIR}")
    exit(1)

for meta_file in sorted(ACI_DIR.rglob("*metadata*.csv")):
    try:
        meta_df = pd.read_csv(meta_file)
        
        # Find matching src-tgt file
        src_tgt_candidates = list(meta_file.parent.glob("*src-tgt*.csv"))
        if not src_tgt_candidates:
            continue
        
        src_df = pd.read_csv(src_tgt_candidates[0])
        
        # Merge on encounter_id or id
        merge_key = "encounter_id" if "encounter_id" in src_df.columns else "id"
        if merge_key not in meta_df.columns:
            continue
        
        merged = meta_df.merge(src_df, on=merge_key, how="inner")
        
        for _, row in merged.iterrows():
            dialogue = str(row.get("src", ""))
            note = str(row.get("note") or row.get("tgt", ""))
            
            if len(dialogue) > 100 and len(note) > 100:
                aci_encounters.append({
                    "aci_id": row[merge_key],
                    "gender": str(row.get("gender", "")).upper(),
                    "chief_complaint": str(row.get("cc", "")),
                    "dialogue": dialogue,
                    "note": note,
                })
    
    except Exception as e:
        print(f"  Warning: Could not load {meta_file}: {e}")

print(f"  Loaded {len(aci_encounters)} ACI-Bench encounters")

if not aci_encounters:
    print("  ERROR: No ACI-Bench encounters loaded")
    exit(1)

# ── Classify ACI encounters by specialty ──────────────────────────────────
# Chief complaint keywords → specialty mapping
CC_KEYWORDS = {
    "Cardiology": ["chest", "heart", "cardiac", "bp", "pressure", "palpitation", "angina"],
    "Neurology": ["headache", "seizure", "memory", "tremor", "stroke", "dizzy", "numbness"],
    "Orthopedics": ["knee", "back", "joint", "pain", "shoulder", "hip", "fracture"],
    "Gastroenterology": ["stomach", "bowel", "abdominal", "nausea", "diarrhea", "reflux"],
    "Pulmonology": ["breath", "asthma", "cough", "lung", "wheez", "respiratory"],
    "Psychiatry": ["depression", "anxiety", "mood", "mental", "sleep"],
    "Endocrinology": ["diabetes", "thyroid", "weight", "glucose"],
    "Nephrology": ["kidney", "renal", "dialysis"],
    "Dermatology": ["skin", "rash", "itch"],
}

def classify_chief_complaint(cc_text):
    """Classify ACI encounter by specialty using chief complaint keywords."""
    cc_lower = cc_text.lower()
    for specialty, keywords in CC_KEYWORDS.items():
        if any(kw in cc_lower for kw in keywords):
            return specialty
    return "General Medicine"

for aci in aci_encounters:
    aci["specialty"] = classify_chief_complaint(aci["chief_complaint"])

specialty_dist = Counter(aci["specialty"] for aci in aci_encounters)
print(f"\n  ACI-Bench specialty distribution:")
for spec, count in sorted(specialty_dist.items(), key=lambda x: -x[1]):
    print(f"    {spec:<25} {count}")

# ── Load golden patients ──────────────────────────────────────────────────
golden_ids = {json.loads(line)["patient_id"] for line in open(GOLDEN)}
patients_df = pd.read_csv(SYNTHEA_DIR / "patients.csv")

# Load last encounter per golden patient
matches = [
    json.loads(line) for line in open(MATCHES)
    if json.loads(line)["patient_id"] in golden_ids
]

by_patient = defaultdict(list)
for m in matches:
    by_patient[m["patient_id"]].append(m)

# ── Match each golden patient to best ACI encounter ───────────────────────
OUTPUT.unlink(missing_ok=True)
matched_count = 0
aci_used = set()
match_stats = {"specialty_gender": 0, "specialty_only": 0, "general_fallback": 0}

print(f"\nMatching {len(golden_ids)} golden patients to ACI-Bench...")

for pid in sorted(golden_ids):
    pt_row = patients_df[patients_df["Id"] == pid].iloc[0]
    gender = pt_row["GENDER"]
    
    # Get last encounter (showcase)
    encs = sorted(by_patient[pid], key=lambda x: x["encounter_date"])
    showcase = encs[-1]
    specialty = showcase["specialty"]
    
    # Try to find best match: specialty + gender
    candidates = [
        aci for aci in aci_encounters
        if aci["specialty"] == specialty
        and aci["gender"] == gender
        and aci["aci_id"] not in aci_used
    ]
    
    match_type = None
    if candidates:
        match_type = "specialty_gender"
    else:
        # Fallback 1: specialty only
        candidates = [
            aci for aci in aci_encounters
            if aci["specialty"] == specialty
            and aci["aci_id"] not in aci_used
        ]
        if candidates:
            match_type = "specialty_only"
        else:
            # Fallback 2: General Medicine
            candidates = [
                aci for aci in aci_encounters
                if aci["specialty"] == "General Medicine"
                and aci["aci_id"] not in aci_used
            ]
            if candidates:
                match_type = "general_fallback"
    
    if candidates:
        best_aci = candidates[0]
        aci_used.add(best_aci["aci_id"])
        matched_count += 1
        match_stats[match_type] += 1
        
        with open(OUTPUT, "a") as f:
            f.write(json.dumps({
                "patient_id": pid,
                "encounter_id": showcase["encounter_id"],
                "encounter_date": showcase["encounter_date"],
                "patient_specialty": specialty,
                "patient_gender": gender,
                "dialogue": best_aci["dialogue"],
                "note_text": best_aci["note"],
                "source": "aci_bench",
                "aci_id": best_aci["aci_id"],
                "aci_specialty": best_aci["specialty"],
                "aci_gender": best_aci["gender"],
                "chief_complaint": best_aci["chief_complaint"],
                "match_type": match_type,
            }) + "\n")
        
        print(f"  ✓ {pid} → ACI {best_aci['aci_id']} "
              f"({best_aci['specialty']}, {best_aci['gender']}, {match_type})")
    else:
        print(f"  ✗ {pid} — no ACI match (specialty: {specialty}, gender: {gender})")
        
        # For unmatched, check if they have MedSynth dialogue
        if showcase.get("best_note_dialogue"):
            with open(OUTPUT, "a") as f:
                f.write(json.dumps({
                    "patient_id": pid,
                    "encounter_id": showcase["encounter_id"],
                    "encounter_date": showcase["encounter_date"],
                    "patient_specialty": specialty,
                    "patient_gender": gender,
                    "dialogue": showcase["best_note_dialogue"],
                    "note_text": showcase.get("best_note_text", ""),
                    "source": "medsynth",
                    "match_type": "medsynth_fallback",
                }) + "\n")
            matched_count += 1
            print(f"    → Using MedSynth dialogue instead")

print(f"\n{'='*60}")
print(f"MATCHING COMPLETE")
print(f"{'='*60}")
print(f"Matched: {matched_count}/{len(golden_ids)} golden patients")
print(f"Coverage: {matched_count/len(golden_ids)*100:.0f}%")
print(f"\nMatch quality breakdown:")
print(f"  Specialty + Gender: {match_stats['specialty_gender']}")
print(f"  Specialty only:     {match_stats['specialty_only']}")
print(f"  General fallback:   {match_stats['general_fallback']}")
print(f"\nOutput: {OUTPUT}")
```

---

## Script 07 — Assemble Corpus (UPDATED)

**File:** `data_prep/scripts/07_assemble_corpus.py`

Only needs minor updates to read from the new adapted_notes structure:

```python
# In the notes.jsonl section, update to read new fields:

for enc_id, note in notes.items():
    if note.get("patient_id") not in selected:
        continue
    
    write_jsonl(CORPUS_DIR / "notes.jsonl", {
        "note_id":          note["note_id"],
        "encounter_id":     enc_id,
        "patient_id":       note["patient_id"],
        "note_text":        note["note_text"],
        "reference_source": note.get("reference_source", ""),
        "num_prior_visits": note.get("num_prior_visits_in_context", 0),  # NEW
        "adaptation_model": note.get("adaptation_model", MODEL),          # NEW
        "is_showcase":      note.get("is_showcase", False),
    })
    counts["notes"] += 1

# In the dialogues.jsonl section, read from aci_showcase_dialogues.jsonl:

print("Writing dialogues.jsonl...")
dlg_idx = 0
aci_dialogues = {
    json.loads(line)["encounter_id"]: json.loads(line)
    for line in open(REPO_ROOT / "data/staging/aci_showcase_dialogues.jsonl")
}

for enc_id, dlg_data in aci_dialogues.items():
    write_jsonl(CORPUS_DIR / "dialogues.jsonl", {
        "dialogue_id":      f"dlg_{dlg_idx:06d}",
        "encounter_id":     enc_id,
        "patient_id":       dlg_data["patient_id"],
        "dialogue_text":    dlg_data["dialogue"],
        "source":           dlg_data["source"],
        "match_type":       dlg_data.get("match_type", ""),
        "is_showcase":      True,
    })
    dlg_idx += 1
    counts["dialogues"] += 1
```

---

## Implementation Sequence

### **Prerequisites**
```bash
cd scribe-iq/data_prep

# Ensure you have:
# - data/staging/selected_patients_golden.jsonl (19 patients)
# - data/staging/match_results.jsonl (269 encounters)
# - data/raw/aci_bench/ (cloned ACI-Bench repo)
# - data/raw/synthea/csv/ (Synthea outputs)

# Set up environment
export GROQ_API_KEY=your_key_here
```

### **Day 1: Longitudinal Context**
```bash
python scripts/05.5_extract_longitudinal_context.py
```
**Output:** `patient_longitudinal_context.jsonl` (269 records)

**Verify:**
```bash
wc -l data/staging/patient_longitudinal_context.jsonl
# Should show 269 lines

head -1 data/staging/patient_longitudinal_context.jsonl | python -m json.tool
# Should show structure with prior_visits array
```

### **Day 2-3: Adapt Notes**
```bash
python scripts/06_adapt_notes.py
```
**Output:** `adapted_notes.jsonl` (~250 prior visit notes)

**Runtime:** ~20-30 minutes for 250 notes on Groq free tier

**Verify:**
```bash
wc -l data/staging/adapted_notes.jsonl
# Should show ~250 lines (one per prior visit with reference note)

# Check a few adapted notes
grep -A1 "note_text" data/staging/adapted_notes.jsonl | head -20
```

### **Day 4: Match ACI-Bench Dialogues**
```bash
python scripts/06.5_match_aci_to_golden.py
```
**Output:** `aci_showcase_dialogues.jsonl` (19 showcase dialogues)

**Verify:**
```bash
wc -l data/staging/aci_showcase_dialogues.jsonl
# Should show 19 lines (one per patient)

# Check match quality
grep "match_type" data/staging/aci_showcase_dialogues.jsonl | sort | uniq -c
```

### **Day 5: Assemble Corpus**
```bash
python scripts/07_assemble_corpus.py
```
**Output:** Complete corpus in `data/clinical_corpus/`

### **Day 6-7: Build Simple UI**

Create a basic React demo with:
- Patient selector (19 golden patients)
- Pre-meeting summary (auto-generated from adapted notes + Synthea)
- Showcase encounter viewer (dialogue + note side-by-side)

---

## Expected Outputs

### **patient_longitudinal_context.jsonl** (269 records)
```json
{
  "patient_id": "abc123",
  "encounter_id": "enc_456",
  "encounter_date": "2024-06-15T10:30:00Z",
  "prior_visits": [
    {
      "date": "2024-03-10",
      "reason": "Follow-up for hypertension",
      "conditions": ["Essential hypertension", "Type 2 diabetes"],
      "medications": ["Metoprolol 50mg daily", "Metformin 1000mg BID"],
      "key_observations": ["BP: 138/84 mmHg", "HbA1c: 7.2 %"]
    },
    {
      "date": "2024-01-05",
      "reason": "Annual physical",
      "conditions": ["Essential hypertension", "Type 2 diabetes"],
      "medications": ["Metoprolol 25mg daily", "Metformin 500mg BID"],
      "key_observations": ["BP: 145/90 mmHg", "HbA1c: 7.8 %"]
    }
  ],
  "num_prior_visits": 2
}
```

### **adapted_notes.jsonl** (~250 records)
```json
{
  "note_id": "note_000042",
  "encounter_id": "enc_456",
  "patient_id": "abc123",
  "encounter_date": "2024-06-15T10:30:00Z",
  "note_text": "SUBJECTIVE:\nPatient returns for follow-up of hypertension and type 2 diabetes. Since last visit in March, reports good compliance with medications. BP at home has been running 135-140/80-85. No chest pain, palpitations, or dyspnea on exertion...",
  "reference_source": "medsynth",
  "reference_note_id": "ms_003421",
  "match_score": 0.78,
  "num_prior_visits_in_context": 2,
  "adaptation_model": "llama-3.1-70b-versatile",
  "is_showcase": false,
  "has_dialogue": false
}
```

### **aci_showcase_dialogues.jsonl** (19 records)
```json
{
  "patient_id": "abc123",
  "encounter_id": "enc_789",
  "encounter_date": "2024-09-20T14:00:00Z",
  "patient_specialty": "Cardiology",
  "patient_gender": "M",
  "dialogue": "Doctor: Good afternoon, how have you been feeling since your last visit?\nPatient: Pretty good overall, though I've had some chest tightness when I climb stairs...",
  "note_text": "CHIEF COMPLAINT: Chest tightness on exertion\n\nSUBJECTIVE: 67-year-old male with history of CAD, HTN, T2DM returns for cardiology follow-up...",
  "source": "aci_bench",
  "aci_id": "aci_12345",
  "aci_specialty": "Cardiology",
  "aci_gender": "M",
  "chief_complaint": "Chest tightness with activity",
  "match_type": "specialty_gender"
}
```

---

## Validation Checklist

After running all scripts, verify:

✅ **Longitudinal context:**
```bash
# Each encounter should have 0-3 prior visits
jq '.num_prior_visits' data/staging/patient_longitudinal_context.jsonl | sort | uniq -c
```

✅ **Adapted notes reference history:**
```bash
# Spot-check 5 random notes
shuf -n 5 data/staging/adapted_notes.jsonl | jq -r '.note_text' | head -50
# Look for phrases like "since last visit", "improved from", "previously", etc.
```

✅ **ACI-Bench coverage:**
```bash
# Should have 19 showcase dialogues
wc -l data/staging/aci_showcase_dialogues.jsonl

# Check match quality distribution
jq -r '.match_type' data/staging/aci_showcase_dialogues.jsonl | sort | uniq -c
```

✅ **No missing showcase encounters:**
```bash
# All 19 golden patients should have showcase dialogue
diff \
  <(jq -r '.patient_id' data/staging/selected_patients_golden.jsonl | sort) \
  <(jq -r '.patient_id' data/staging/aci_showcase_dialogues.jsonl | sort)
# Should be empty (no diff)
```

---

## Cost & Timeline

**Estimated costs:**
- Groq free tier: $0 (14,400 req/day, 250 notes fits easily)
- All datasets: $0 (open access)
- **Total: $0**

**Timeline:**
- Script 05.5 (context): 30 seconds
- Script 06 (adaptation): 20-30 minutes
- Script 06.5 (ACI matching): 1 minute
- Script 07 (assembly): 5 minutes
- Script 08-09 (validation): 2 minutes
- **Total: ~40 minutes of runtime + 1 day of your time to run/verify**

---

## What This Gets You

✅ **19 patients** with full longitudinal history  
✅ **~250 adapted notes** that reference prior visits naturally  
✅ **19 showcase dialogues** (ACI-Bench quality)  
✅ **Working dataset** ready for UI demo in 1 week  
✅ **No over-engineering** — just what's needed  

---

## Coding Agent Instructions

1. **Create directory structure** as shown above
2. **Implement scripts in order:** 05.5 → 06 → 06.5 → update 07
3. **Run each script** and verify output before moving to next
4. **Spot-check quality:** Read 5-10 adapted notes to confirm they reference prior history
5. **Build simple UI** once data is ready

Each script is independent and can be debugged in isolation.
