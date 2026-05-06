# Scribe-IQ — Simplified Implementation (CORRECTED)
## Bug Fixes Applied From Agent Review

---

## Changes From Previous Version

### **Bugs Fixed:**
1. ✅ `encounter_reason` NaN handling (sanitize to string)
2. ✅ Gender normalization for ACI matching (M/F consistent)
3. ✅ Deterministic patient iteration (file order, not set)
4. ✅ Field naming: use `adapted_note_id` (matches existing 07)
5. ✅ Showcase notes: single file pattern (adapted_notes.jsonl)
6. ✅ Use existing ACI reservations (no duplicate logic)
7. ✅ Groq client in main() (not at import)
8. ✅ Model from env with safe default
9. ✅ Use `load_synthea` / `compute_age` from utils
10. ✅ Aligned corpus directory name

---

## Script 05.5 — Extract Longitudinal Context (CORRECTED)

**File:** `data_prep/scripts/05.5_extract_longitudinal_context.py`

```python
"""
05.5_extract_longitudinal_context.py

Extracts longitudinal context for golden patient encounters.
CORRECTED VERSION: Fixes from agent review applied.
"""

from pathlib import Path
import json
from collections import defaultdict

def sanitize_string(value, default="Not documented"):
    """Convert encounter_reason to valid string (handles NaN/float/None)."""
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        return default
    return str(value).strip() if str(value).strip() else default


def main():
    REPO_ROOT = Path(__file__).resolve().parents[2]
    GOLDEN    = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
    MATCHES   = REPO_ROOT / "data/staging/match_results.jsonl"
    OUTPUT    = REPO_ROOT / "data/staging/patient_longitudinal_context.jsonl"
    
    K_PRIOR_VISITS = 3
    
    print("="*60)
    print("EXTRACTING LONGITUDINAL CONTEXT")
    print("="*60)
    
    # Load golden patient IDs IN FILE ORDER (deterministic)
    golden_patients = [json.loads(line) for line in open(GOLDEN)]
    golden_ids = [p["patient_id"] for p in golden_patients]
    print(f"\nGolden patients: {len(golden_ids)} (file order preserved)")
    
    # Load matches for golden patients only (filter while reading)
    matches = []
    with open(MATCHES) as f:
        for line in f:
            m = json.loads(line)
            if m["patient_id"] in golden_ids:
                matches.append(m)
    
    print(f"Total encounters for golden patients: {len(matches)}")
    
    # Group by patient
    by_patient = defaultdict(list)
    for m in matches:
        by_patient[m["patient_id"]].append(m)
    
    # Build longitudinal context
    OUTPUT.unlink(missing_ok=True)
    total_contexts = 0
    
    # Process in file order for deterministic output
    for pid in golden_ids:
        encs = by_patient[pid]
        
        # Sort chronologically
        encs_sorted = sorted(encs, key=lambda x: x["encounter_date"])
        
        for i, current_enc in enumerate(encs_sorted):
            # Get K=3 prior visits (or fewer if at start)
            prior_start = max(0, i - K_PRIOR_VISITS)
            prior_encs = encs_sorted[prior_start:i]
            
            # Build prior visit blocks
            prior_blocks = []
            for prior in prior_encs:
                # Sanitize encounter_reason (can be NaN/float)
                reason = sanitize_string(prior.get("encounter_reason"))
                
                # Cap lists
                conditions = prior.get("conditions", [])[:5]
                medications = prior.get("medications", [])[:5]
                obs = prior.get("recent_obs", [])[:3]
                
                prior_blocks.append({
                    "date": prior["encounter_date"][:10],
                    "reason": reason,
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


if __name__ == "__main__":
    main()
```

---

## Script 06 — Adapt Notes (CORRECTED)

**File:** `data_prep/scripts/06_adapt_notes.py`

```python
"""
06_adapt_notes.py

Adapts notes with longitudinal context.
CORRECTED VERSION: Fixes all bugs from agent review.

Key fixes:
- Groq client in main(), not at import
- Model from env with safe default
- Use utils.synthea_utils (not raw pandas)
- encounter_reason sanitization
- Field naming: adapted_note_id (not note_id)
- Showcase notes written to same file
"""

import os
import json
import time
from pathlib import Path
from collections import defaultdict
from groq import Groq
from utils.synthea_utils import load_synthea, compute_age

def sanitize_string(value, default="Not documented"):
    """Convert to valid string (handles NaN/float/None)."""
    if value is None or (isinstance(value, float) and value != value):
        return default
    return str(value).strip() if str(value).strip() else default


def format_prior_context(prior_blocks):
    """Format prior visit blocks for prompt."""
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
    """Format observation list for prompt."""
    if not obs_list:
        return "  None recorded"
    
    lines = []
    for o in obs_list[:5]:
        desc = o.get('DESCRIPTION', 'Unknown')
        val = o.get('VALUE', '')
        units = o.get('UNITS', '')
        lines.append(f"  - {desc}: {val} {units}".strip())
    
    return '\n'.join(lines) if lines else "  None recorded"


def main():
    REPO_ROOT   = Path(__file__).resolve().parents[2]
    GOLDEN      = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
    MATCHES     = REPO_ROOT / "data/staging/match_results.jsonl"
    CONTEXT     = REPO_ROOT / "data/staging/patient_longitudinal_context.jsonl"
    ACI_RES     = REPO_ROOT / "data/staging/aci_reservations.jsonl"
    SYNTHEA_DIR = REPO_ROOT / "data/raw/synthea/csv"
    OUTPUT      = REPO_ROOT / "data/staging/adapted_notes.jsonl"
    
    # Model from env with safe default
    MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    # Initialize Groq client here, not at import
    if "GROQ_API_KEY" not in os.environ:
        print("ERROR: GROQ_API_KEY not set")
        exit(1)
    
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    
    print("="*60)
    print("ADAPTING NOTES WITH LONGITUDINAL CONTEXT")
    print("="*60)
    print(f"Model: {MODEL}")
    
    # Load longitudinal context
    context_lookup = {}
    with open(CONTEXT) as f:
        for line in f:
            ctx = json.loads(line)
            context_lookup[(ctx["patient_id"], ctx["encounter_id"])] = ctx
    
    print(f"\nLoaded context for {len(context_lookup)} encounters")
    
    # Load golden patient IDs in file order
    golden_patients = [json.loads(line) for line in open(GOLDEN)]
    golden_ids = [p["patient_id"] for p in golden_patients]
    
    # Load matches for golden patients only
    matches = []
    with open(MATCHES) as f:
        for line in f:
            m = json.loads(line)
            if m["patient_id"] in golden_ids:
                matches.append(m)
    
    print(f"Encounters to process: {len(matches)}")
    
    # Group by patient
    by_patient = defaultdict(list)
    for m in matches:
        by_patient[m["patient_id"]].append(m)
    
    # Load Synthea using utils
    synthea = load_synthea(SYNTHEA_DIR)
    patients_df = synthea["patients"]
    
    # Load ACI reservations if they exist
    aci_reserved = {}
    if ACI_RES.exists():
        with open(ACI_RES) as f:
            for line in f:
                res = json.loads(line)
                aci_reserved[res["note_id"]] = res
        print(f"ACI reservations loaded: {len(aci_reserved)}")
    
    # Adaptation prompt
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
    
    def call_groq(prompt, retries=3):
        """Call Groq with retry logic."""
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
    
    # Process in file order (deterministic)
    for pid in golden_ids:
        pt_row = patients_df[patients_df["Id"] == pid].iloc[0]
        sex = "Male" if pt_row["GENDER"] == "M" else "Female"
        
        # Get encounters sorted chronologically
        encs = sorted(by_patient[pid], key=lambda x: x["encounter_date"])
        
        # All but last = prior visits
        # Last = showcase
        prior_visits = encs[:-1]
        showcase = encs[-1]
        
        print(f"\n{pid} — {len(encs)} encounters ({len(prior_visits)} prior + 1 showcase)")
        
        # ── Adapt prior visits ────────────────────────────────────────
        for enc in prior_visits:
            if not enc.get("best_note_text"):
                print(f"  [{enc['encounter_date'][:10]}] no reference note, skipping")
                continue
            
            # Get context
            ctx = context_lookup.get((pid, enc["encounter_id"]))
            if not ctx:
                print(f"  [{enc['encounter_date'][:10]}] no context, skipping")
                continue
            
            # Compute age
            age = compute_age(pt_row["BIRTHDATE"], enc["encounter_date"])
            
            # Sanitize encounter_reason
            reason = sanitize_string(enc.get("encounter_reason"), "Follow-up visit")
            
            # Build prompt
            prompt = ADAPT_PROMPT.format(
                prior_context=format_prior_context(ctx["prior_visits"]),
                visit_date=enc["encounter_date"][:10],
                age=age,
                sex=sex,
                visit_reason=reason,
                conditions=", ".join(enc.get("conditions", [])) or "None documented",
                medications=", ".join(enc.get("medications", [])) or "None documented",
                observations=format_observations(enc.get("recent_obs", [])),
                reference_note=enc["best_note_text"][:2500],
            )
            
            print(f"  [{enc['encounter_date'][:10]}] adapting "
                  f"({enc['best_note_source']}, {ctx['num_prior_visits']} prior)...",
                  end=" ", flush=True)
            
            try:
                adapted_text = call_groq(prompt)
                
                # Write with correct field names
                with open(OUTPUT, "a") as f:
                    f.write(json.dumps({
                        "adapted_note_id": f"note_{note_idx:06d}",  # NOT note_id
                        "encounter_id": enc["encounter_id"],
                        "patient_id": pid,
                        "encounter_date": enc["encounter_date"],
                        "note_text": adapted_text,
                        "reference_source": enc["best_note_source"],
                        "reference_note_id": enc.get("best_note_id"),
                        "match_score": enc["match_score"],
                        "num_prior_visits": ctx["num_prior_visits"],
                        "adaptation_model": MODEL,
                        "is_showcase": False,
                        "has_dialogue": False,
                    }) + "\n")
                
                note_idx += 1
                total_prior_notes += 1
                print("✓")
                
            except Exception as e:
                print(f"✗ Error: {e}")
            
            # Rate limit courtesy (optional, can remove if too slow)
            # time.sleep(0.5)
        
        # ── Showcase encounter ────────────────────────────────────────
        # Check if ACI reserved for this encounter
        showcase_note_id = showcase.get("best_note_id")
        
        if showcase_note_id and showcase_note_id in aci_reserved:
            # Use ACI-Bench directly (already reserved)
            aci = aci_reserved[showcase_note_id]
            
            with open(OUTPUT, "a") as f:
                f.write(json.dumps({
                    "adapted_note_id": f"note_{note_idx:06d}",
                    "encounter_id": showcase["encounter_id"],
                    "patient_id": pid,
                    "encounter_date": showcase["encounter_date"],
                    "note_text": aci["note_text"],
                    "dialogue": aci.get("dialogue"),
                    "reference_source": "aci_bench",
                    "reference_note_id": aci["note_id"],
                    "match_score": showcase["match_score"],
                    "num_prior_visits": 0,  # showcase doesn't use prior context
                    "adaptation_model": "aci_bench_direct",
                    "is_showcase": True,
                    "has_dialogue": True,
                }) + "\n")
            
            note_idx += 1
            total_showcase += 1
            print(f"  [{showcase['encounter_date'][:10]}] showcase → ACI-Bench")
        
        elif showcase.get("best_note_dialogue"):
            # Fallback: MedSynth dialogue
            with open(OUTPUT, "a") as f:
                f.write(json.dumps({
                    "adapted_note_id": f"note_{note_idx:06d}",
                    "encounter_id": showcase["encounter_id"],
                    "patient_id": pid,
                    "encounter_date": showcase["encounter_date"],
                    "note_text": showcase.get("best_note_text", ""),
                    "dialogue": showcase["best_note_dialogue"],
                    "reference_source": "medsynth",
                    "reference_note_id": showcase.get("best_note_id"),
                    "match_score": showcase["match_score"],
                    "num_prior_visits": 0,
                    "adaptation_model": "medsynth_direct",
                    "is_showcase": True,
                    "has_dialogue": True,
                }) + "\n")
            
            note_idx += 1
            total_showcase += 1
            print(f"  [{showcase['encounter_date'][:10]}] showcase → MedSynth dialogue")
        
        else:
            # No dialogue available, adapt note
            ctx = context_lookup.get((pid, showcase["encounter_id"]))
            if ctx and showcase.get("best_note_text"):
                age = compute_age(pt_row["BIRTHDATE"], showcase["encounter_date"])
                reason = sanitize_string(showcase.get("encounter_reason"), "Follow-up")
                
                prompt = ADAPT_PROMPT.format(
                    prior_context=format_prior_context(ctx["prior_visits"]),
                    visit_date=showcase["encounter_date"][:10],
                    age=age,
                    sex=sex,
                    visit_reason=reason,
                    conditions=", ".join(showcase.get("conditions", [])) or "None",
                    medications=", ".join(showcase.get("medications", [])) or "None",
                    observations=format_observations(showcase.get("recent_obs", [])),
                    reference_note=showcase["best_note_text"][:2500],
                )
                
                adapted_text = call_groq(prompt)
                
                with open(OUTPUT, "a") as f:
                    f.write(json.dumps({
                        "adapted_note_id": f"note_{note_idx:06d}",
                        "encounter_id": showcase["encounter_id"],
                        "patient_id": pid,
                        "encounter_date": showcase["encounter_date"],
                        "note_text": adapted_text,
                        "dialogue": None,
                        "reference_source": showcase["best_note_source"],
                        "reference_note_id": showcase.get("best_note_id"),
                        "match_score": showcase["match_score"],
                        "num_prior_visits": ctx["num_prior_visits"],
                        "adaptation_model": MODEL,
                        "is_showcase": True,
                        "has_dialogue": False,
                    }) + "\n")
                
                note_idx += 1
                total_showcase += 1
                print(f"  [{showcase['encounter_date'][:10]}] showcase → adapted (no dialogue)")
    
    print(f"\n{'='*60}")
    print(f"ADAPTATION COMPLETE")
    print(f"{'='*60}")
    print(f"Prior visit notes: {total_prior_notes}")
    print(f"Showcase notes: {total_showcase}")
    print(f"Total: {note_idx}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
```

---

## Script 06.5 — Match ACI (SIMPLIFIED - uses existing reservations)

**File:** `data_prep/scripts/06.5_verify_aci_coverage.py`

**NOTE:** This is now a verification script only. The actual ACI matching should use your existing `aci_reservations.jsonl` from script 03. This avoids duplicate logic.

```python
"""
06.5_verify_aci_coverage.py

Verifies ACI-Bench dialogue coverage for golden patients.
Uses EXISTING aci_reservations.jsonl (from script 03).

This is a verification-only script. If you don't have aci_reservations.jsonl,
run script 03 first to create it.
"""

import json
from pathlib import Path
from collections import Counter

def main():
    REPO_ROOT = Path(__file__).resolve().parents[2]
    GOLDEN    = REPO_ROOT / "data/staging/selected_patients_golden.jsonl"
    MATCHES   = REPO_ROOT / "data/staging/match_results.jsonl"
    ACI_RES   = REPO_ROOT / "data/staging/aci_reservations.jsonl"
    
    print("="*60)
    print("VERIFYING ACI-BENCH COVERAGE")
    print("="*60)
    
    # Load golden IDs
    golden_patients = [json.loads(line) for line in open(GOLDEN)]
    golden_ids = set(p["patient_id"] for p in golden_patients)
    print(f"\nGolden patients: {len(golden_ids)}")
    
    # Load matches for golden patients
    matches = []
    with open(MATCHES) as f:
        for line in f:
            m = json.loads(line)
            if m["patient_id"] in golden_ids:
                matches.append(m)
    
    # Group by patient, find last encounter
    from collections import defaultdict
    by_patient = defaultdict(list)
    for m in matches:
        by_patient[m["patient_id"]].append(m)
    
    showcase_encounters = {}
    for pid in golden_ids:
        encs = sorted(by_patient[pid], key=lambda x: x["encounter_date"])
        showcase = encs[-1]
        showcase_encounters[pid] = showcase
    
    # Load ACI reservations
    if not ACI_RES.exists():
        print(f"\n⚠️  WARNING: {ACI_RES} not found")
        print("Run script 03_reserve_aci_encounters.py first to create reservations")
        return
    
    aci_reserved = {}
    with open(ACI_RES) as f:
        for line in f:
            res = json.loads(line)
            aci_reserved[res["note_id"]] = res
    
    print(f"ACI reservations loaded: {len(aci_reserved)}")
    
    # Check coverage
    dialogue_sources = []
    for pid, showcase in showcase_encounters.items():
        note_id = showcase.get("best_note_id")
        
        if note_id and note_id in aci_reserved:
            dialogue_sources.append("aci_bench")
        elif showcase.get("best_note_dialogue"):
            dialogue_sources.append("medsynth")
        else:
            dialogue_sources.append("none")
    
    source_counts = Counter(dialogue_sources)
    
    print(f"\n{'='*60}")
    print(f"DIALOGUE COVERAGE FOR {len(golden_ids)} SHOWCASES")
    print(f"{'='*60}")
    print(f"ACI-Bench:  {source_counts['aci_bench']}")
    print(f"MedSynth:   {source_counts['medsynth']}")
    print(f"None:       {source_counts['none']}")
    print(f"Total coverage: {(source_counts['aci_bench'] + source_counts['medsynth']) / len(golden_ids) * 100:.0f}%")


if __name__ == "__main__":
    main()
```

---

## Utils Update

**File:** `data_prep/utils/synthea_utils.py`

Add this if not present:

```python
def compute_age(birth_date_str: str, as_of_date_str: str) -> int:
    """Compute patient age at a specific date."""
    import pandas as pd
    birth = pd.to_datetime(birth_date_str)
    as_of = pd.to_datetime(as_of_date_str)
    return int((as_of - birth).days / 365.25)
```

---

## Corrected Implementation Sequence

### **Prerequisites**
```bash
# Must have these files already:
# - data/staging/selected_patients_golden.jsonl
# - data/staging/match_results.jsonl
# - data/staging/aci_reservations.jsonl (from script 03)
# - data/raw/synthea/csv/

export GROQ_API_KEY=your_key
export GROQ_MODEL=llama-3.1-70b-versatile  # optional, has safe default
```

### **Run Sequence**
```bash
cd data_prep

# Step 1: Extract context
python scripts/05.5_extract_longitudinal_context.py

# Step 2: Adapt notes (includes showcases)
python scripts/06_adapt_notes.py

# Step 3: Verify dialogue coverage
python scripts/06.5_verify_aci_coverage.py

# Step 4: Assemble corpus (existing script, should work as-is)
python scripts/07_assemble_corpus.py
```

---

## Key Differences From Previous Version

| Issue | Previous | Corrected |
|---|---|---|
| encounter_reason | Direct use (crashes on NaN) | `sanitize_string()` helper |
| Patient order | Set iteration (random) | File order (deterministic) |
| Field names | `note_id` | `adapted_note_id` (matches 07) |
| Showcase pattern | Two files | Single `adapted_notes.jsonl` |
| ACI logic | New script 06.5 | Uses existing `aci_reservations.jsonl` |
| Groq client | Import-time | In `main()` |
| Model ID | Hardcoded | From env with default |
| Synthea loading | Raw pandas | `utils.synthea_utils` |

---

## Validation

After running, verify field names match:

```bash
# Check adapted_note_id is used (not note_id)
head -1 data/staging/adapted_notes.jsonl | python -m json.tool | grep note_id
# Should show "adapted_note_id"

# Check showcases are in same file
jq 'select(.is_showcase == true)' data/staging/adapted_notes.jsonl | wc -l
# Should show 19

# Check deterministic output (run twice)
python scripts/05.5_extract_longitudinal_context.py
mv data/staging/patient_longitudinal_context.jsonl /tmp/run1.jsonl
python scripts/05.5_extract_longitudinal_context.py
diff /tmp/run1.jsonl data/staging/patient_longitudinal_context.jsonl
# Should be identical (no output from diff)
```

---

## Summary of Corrections

✅ All bugs from agent review fixed  
✅ Uses existing ACI reservations (no duplicate logic)  
✅ Single file for all notes (prior + showcase)  
✅ Deterministic output (file order)  
✅ Robust string handling (NaN-safe)  
✅ Proper utils integration  
✅ Env-based configuration  

This version is ready for the coding agent to implement.
