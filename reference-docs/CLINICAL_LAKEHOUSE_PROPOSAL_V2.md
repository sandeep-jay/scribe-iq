# Scribe-IQ Clinical Lakehouse — v2
### A Synthetic Clinical Data Pipeline Joining Synthea Patient Records with AGBonnet Clinical Language

---

> **Historical / architectural proposal.** This document describes the **lakehouse-shaped precursor** design for assembling a synthetic clinical corpus. In **this repository today**, the **canonical runnable corpus builder** is **`data_prep/`** plus **`reference-docs/SCRIBE_IQ_DATA_PIPELINE_V2_AGENT.md`**. Use those paths when executing pipelines on disk; use this proposal for rationale and evolution.


## 1. Project Goal

Build a curated synthetic clinical data lakehouse that combines two public datasets into a single, coherent corpus:

- **Synthea** — provides the patient spine: real longitudinal encounter history, demographics, conditions, medications, procedures, and lab results
- **AGBonnet/augmented-clinical-notes** — provides the clinical language layer: realistic clinical notes, doctor-patient dialogues, and structured visit summaries

The join between these two datasets produces something neither can provide alone: **synthetic patients with real clinical history and real clinical language** — the foundation Scribe-IQ needs to demo pre-meeting summaries, note generation, and transcription features coherently.

---

## 2. Why Two Datasets

### The problem with AGBonnet alone

AGBonnet is a corpus of 30,000 isolated PubMed Central case studies. Every row is a different patient from a different paper. There is no shared patient identity across rows. Grouping encounters by compatibility produces collages, not people — conditions that don't relate to each other, medication histories that don't make clinical sense, timelines that are arbitrary.

A pre-meeting summary built on that collapses under any scrutiny.

### The problem with Synthea alone

Synthea produces realistic longitudinal patient records but its clinical notes are templated and formulaic. The language does not read like a real clinician wrote it. There are no doctor-patient dialogues. The note text cannot drive a convincing transcription or note generation demo.

### The solution: join them

```
Synthea patient + encounter timeline     AGBonnet note + dialogue + summary
         ↓                                          ↓
    patient spine                           clinical language
         └──────────────── join ────────────────────┘
                               ↓
              synthetic patient with real history
              and real clinical language
```

For each Synthea encounter, find the best-matching AGBonnet row by specialty and condition overlap, attach its note, dialogue, and summary. The result is a corpus where:

- Patient continuity is real (Synthea)
- Clinical language is real (AGBonnet)
- Pre-meeting summaries are coherent across visits
- Transcription demos have realistic dialogue
- Note generation has realistic reference notes

---

## 3. Current State

The following work is already complete on the AGBonnet side:

| Phase | Status | Output |
|---|---|---|
| Source validation | ✅ Done | `validate_dataset.py` **PROCEED** (see logs) |
| Staging | ✅ Done | `data/staging/manifest.json`, `AGBonnet__augmented-clinical-notes/train.parquet` |
| Specialty classification | ✅ Done | `data/staging/specialty_predictions.jsonl` |

Classification results:
- 30,000 rows classified
- Average confidence: 0.875
- Low confidence rows: 2,020 (6.7%)
- Device: MPS, runtime: ~10 minutes

Work remaining is described in full in the phases below.

---

## 4. Data Layers

```
raw  →  staging  →  curated  →  application
```

### Raw
Immutable source data. Never modified.

```
data/raw/
  agbonnet/          ← Hugging Face download
  synthea/           ← Synthea generated output
```

### Staging
Validated, enriched, and join-ready intermediate data for both sources.

```
data/staging/
  agbonnet/
    manifest.json
    train.parquet
    dataset_validation_report.md
    specialty_predictions.jsonl          ← done
    specialty_prediction_summary.json    ← done
    join_keys.jsonl                      ← next
    join_keys_summary.json
    quality_tiered_encounters.jsonl
    quality_summary.json
  synthea/
    patients.parquet
    encounters.parquet
    conditions.parquet
    medications.parquet
    procedures.parquet
    observations.parquet
    careplans.parquet
    synthea_staging_report.md
```

### Curated
Final enriched corpus ready for Scribe-IQ consumption.

```
data/clinical_corpus/
  patients.jsonl
  encounters.jsonl
  notes.jsonl
  conditions.jsonl
  medications.jsonl
  procedures.jsonl
  observations.jsonl
  dialogues.jsonl
  source_provenance.jsonl
  join_audit.jsonl
  manifest.json
  audit_report.md
  dataset_card.md
```

### Application
Scribe-IQ reads only from `data/clinical_corpus/`. No dependency on Hugging Face or Synthea raw files at runtime.

---

## 5. Input Datasets

### AGBonnet/augmented-clinical-notes

30,000 clinical note triplets from PubMed Central case studies.

| Field | Description |
|---|---|
| `idx` | Unique row identifier |
| `conversation` | Synthetic GPT-3.5 patient-doctor dialogue |
| `note` | Truncated clinical note |
| `full_note` | Full PMC-Patients clinical note |
| `summary` | GPT-4 structured JSON summary |

**Known limitations:**
- Every row is an independent patient — no longitudinal continuity
- Dialogues are GPT-3.5 generated and tend to be formulaic
- Summaries were generated from truncated notes, not full notes
- Some rows contain prompt leaks
- Age and sex are often missing or expressed as free text

### Synthea

Synthea is an open-source synthetic patient generator that produces realistic longitudinal health records. Generate a population appropriate for the specialty distribution found in AGBonnet classification output.

**Recommended generation parameters:**
- Population: 5,000–10,000 patients
- Modules: general + specialty-relevant (cardiovascular, neurological, gastrointestinal, orthopedic, dermatological, pulmonary, renal, endocrine, infectious disease)
- Output format: CSV
- Seed: fixed, for reproducibility

**Synthea tables used:**

| Table | Description |
|---|---|
| `patients.csv` | Demographics, birth date, sex, ethnicity |
| `encounters.csv` | Visit dates, encounter class, reason code |
| `conditions.csv` | SNOMED condition codes + descriptions, onset/stop dates |
| `medications.csv` | RxNorm codes, drug names, doses, start/stop |
| `procedures.csv` | SNOMED procedure codes + descriptions |
| `observations.csv` | LOINC codes, lab results, vitals |
| `careplans.csv` | Care plan activities and goals |

---

## 6. Output Corpus Files

### `patients.jsonl`
Sourced from Synthea. One record per patient. Stable across all encounters.

```json
{
  "patient_id": "syn_pat_000001",
  "source": "synthea",
  "sex": "F",
  "birth_date": "2008-04-12",
  "age_at_index": 16,
  "age_band": "pediatric",
  "ethnicity": "hispanic",
  "primary_specialty": "Neurology",
  "encounter_count": 5,
  "quality_tier": "gold"
}
```

### `encounters.jsonl`
Sourced from Synthea. One record per encounter. Enriched with AGBonnet join metadata.

```json
{
  "encounter_id": "syn_enc_000001",
  "patient_id": "syn_pat_000001",
  "encounter_date": "2023-06-14",
  "encounter_class": "outpatient",
  "specialty": "Neurology",
  "reason_description": "Medication review - bipolar disorder",
  "agbonnet_source_row_id": "155216",
  "join_confidence": "high",
  "join_score": 0.84,
  "quality_tier": "gold"
}
```

### `notes.jsonl`
Sourced from AGBonnet. Attached to Synthea encounters via join.

```json
{
  "note_id": "note_000001",
  "encounter_id": "syn_enc_000001",
  "patient_id": "syn_pat_000001",
  "agbonnet_source_row_id": "155216",
  "full_note": "...",
  "reference_note": "...",
  "summary_raw": "{...}",
  "summary_parsed": {}
}
```

### `dialogues.jsonl`
Sourced from AGBonnet. The doctor-patient conversation attached to each encounter.

```json
{
  "dialogue_id": "dlg_000001",
  "encounter_id": "syn_enc_000001",
  "patient_id": "syn_pat_000001",
  "agbonnet_source_row_id": "155216",
  "conversation_text": "Doctor: Good morning...\nPatient: ..."
}
```

### `conditions.jsonl`
Sourced from Synthea. Longitudinal condition history per patient.

```json
{
  "condition_id": "syn_cond_000001",
  "patient_id": "syn_pat_000001",
  "encounter_id": "syn_enc_000001",
  "snomed_code": "13746004",
  "description": "Bipolar disorder",
  "onset_date": "2019-03-01",
  "stop_date": null,
  "is_active": true
}
```

### `medications.jsonl`
Sourced from Synthea. Full medication history with start/stop dates.

```json
{
  "medication_id": "syn_med_000001",
  "patient_id": "syn_pat_000001",
  "encounter_id": "syn_enc_000001",
  "rxnorm_code": "213463",
  "description": "Olanzapine 5 MG Oral Tablet",
  "start_date": "2023-06-14",
  "stop_date": null,
  "is_active": true,
  "reason_description": "Bipolar disorder"
}
```

### `procedures.jsonl`
Sourced from Synthea.

```json
{
  "procedure_id": "syn_proc_000001",
  "patient_id": "syn_pat_000001",
  "encounter_id": "syn_enc_000001",
  "snomed_code": "710824005",
  "description": "Assessment of mental status",
  "procedure_date": "2023-06-14"
}
```

### `observations.jsonl`
Sourced from Synthea. Lab results, vitals, and clinical measurements.

```json
{
  "observation_id": "syn_obs_000001",
  "patient_id": "syn_pat_000001",
  "encounter_id": "syn_enc_000001",
  "loinc_code": "2823-3",
  "description": "Potassium [Moles/volume] in Serum or Plasma",
  "value": "4.1",
  "units": "mmol/L",
  "observation_date": "2023-06-14"
}
```

### `source_provenance.jsonl`
Full lineage for every curated record.

```json
{
  "encounter_id": "syn_enc_000001",
  "patient_id": "syn_pat_000001",
  "synthea_encounter_id": "abc-123-def",
  "agbonnet_source_row_id": "155216",
  "agbonnet_predicted_specialty": "Neurology",
  "agbonnet_classifier_confidence": 0.91,
  "join_score": 0.84,
  "join_confidence": "high",
  "join_method": "specialty_ageBand_conditionOverlap",
  "join_fallback": false
}
```

### `join_audit.jsonl`
One record per join attempt. Documents match quality across the corpus.

```json
{
  "synthea_encounter_id": "abc-123-def",
  "agbonnet_source_row_id": "155216",
  "specialty_match": true,
  "age_band_match": true,
  "condition_overlap_score": 0.67,
  "composite_score": 0.84,
  "join_confidence": "high",
  "fallback_used": false,
  "fallback_reason": null
}
```

---

## 7. Transformation Phases

### Phase 0 — AGBonnet Source Validation ✅ DONE
### Phase 1 — AGBonnet Specialty Classification ✅ DONE

---

### Phase 2 — AGBonnet Join Key Extraction

**Goal:** Extract the minimum fields needed to make the Synthea join clinically coherent. This is not a full clinical extraction — it is a join preparation step.

**Input:** `data/staging/agbonnet/train.parquet` + `specialty_predictions.jsonl`

**Extraction targets from `summary` JSON:**

| Field | Source in summary | Normalization |
|---|---|---|
| `age` | `patient information.age` | Text → integer (`"Sixteen years old"` → `16`) |
| `age_band` | derived from age | pediatric / young_adult / adult / senior / unknown |
| `sex` | `patient information.sex` | → `M` / `F` / `null` |
| `conditions` | `patient medical history` + diagnosis fields | List of normalized strings |
| `medications` | `treatments[].name` | List of drug name strings |
| `visit_reason` | `visit motivation` | String, kept as-is |

**What is not extracted here:**
- Symptoms (too collapsed to be useful as join keys)
- Investigations (not in summary for most rows)
- Dosages (too specific to match reliably against Synthea)
- Discharge / follow-up (not needed for join)

**Output schema:**
```json
{
  "source_row_id": "155216",
  "predicted_specialty": "Neurology",
  "classifier_confidence": 0.91,
  "age": 16,
  "age_band": "pediatric",
  "sex": "F",
  "conditions": ["bipolar affective disorder", "tardive dystonia", "hypothyroidism"],
  "medications": ["olanzapine", "trihexyphenidyl", "sodium valproate", "lithium"],
  "visit_reason": "Discomfort in the neck and lower back, restriction of body movements",
  "summary_parse_success": true,
  "quality_flags": []
}
```

**Quality flags assigned at this phase:**

- `summary_parse_failure` — `json.loads` failed
- `missing_age` — age not present or not parseable
- `missing_sex` — sex not present
- `missing_conditions` — no conditions extractable
- `low_classifier_confidence` — confidence < 0.70

**Outputs:**
- `data/staging/agbonnet/join_keys.jsonl`
- `data/staging/agbonnet/join_keys_summary.json`

---

### Phase 3 — AGBonnet Quality Tiering

**Goal:** Assign a quality tier to every AGBonnet row based on join readiness, not clinical completeness.

**Tiers:**

| Tier | Criteria |
|---|---|
| **Gold** | Parse success · Confidence ≥ 0.80 · Age present · Sex present · ≥ 1 condition · Conversation present · Full note present |
| **Silver** | Parse success · Confidence ≥ 0.70 · Conversation present · Full note present |
| **Bronze** | Full note present · Conversation present · Everything else missing or low confidence |
| **Excluded** | Missing full note · Missing conversation · Duplicate conversation · Parse failure with no recoverable fields |

**Outputs:**
- `data/staging/agbonnet/quality_tiered_encounters.jsonl`
- `data/staging/agbonnet/quality_summary.json`

---

### Phase 4 — Synthea Generation and Staging

**Goal:** Generate a Synthea population sized and specialty-distributed to match the AGBonnet corpus, then stage it into parquet.

**Generation:**

Run Synthea locally with a fixed seed. Target population of 5,000–10,000 patients. Enable specialty modules aligned with the AGBonnet specialty distribution:

| Specialty | AGBonnet rows | Synthea module |
|---|---|---|
| Gastroenterology | 4,966 | `ibs`, `crohn`, `colorectal_cancer` |
| Neurology | 4,839 | `epilepsy`, `alzheimers`, `stroke` |
| Cardiology | 4,021 | `heart_disease`, `hypertension` |
| Orthopedics | 3,722 | `osteoporosis`, `joint_replacement` |
| Dentistry | 2,560 | `dental` |
| Dermatology | 2,277 | `dermatitis` |
| Pulmonology | 2,097 | `asthma`, `copd`, `lung_cancer` |
| Nephrology | 1,207 | `kidney_disease` |
| Ophthalmology | 985 | `macular_degeneration`, `cataracts` |
| Endocrinology | 970 | `diabetes` |
| Infectious Disease | 903 | `hiv`, `sepsis` |
| Urology | 790 | `urinary_tract_infections`, `prostate` |
| Otorhinolaryngology | 663 | `ear_infections` |

**Staging tasks:**
1. Load all Synthea CSV outputs into parquet
2. Normalize column names to snake_case
3. Assign stable `syn_pat_XXXXXX` and `syn_enc_XXXXXX` IDs
4. Derive `age_at_encounter` and `age_band` per encounter
5. Map Synthea encounter reason codes to specialty labels
6. Validate row counts, date ranges, referential integrity
7. Produce staging report

**Outputs:**
- `data/staging/synthea/patients.parquet`
- `data/staging/synthea/encounters.parquet`
- `data/staging/synthea/conditions.parquet`
- `data/staging/synthea/medications.parquet`
- `data/staging/synthea/procedures.parquet`
- `data/staging/synthea/observations.parquet`
- `data/staging/synthea/careplans.parquet`
- `data/staging/synthea/synthea_staging_report.md`

---

### Phase 5 — Synthea Specialty Mapping

**Goal:** Label every Synthea encounter with a specialty that can be matched against AGBonnet predictions.

Synthea does not natively output specialty labels. Derive them from:

1. **Encounter reason code** — SNOMED reason codes map to specialty (primary signal)
2. **Active conditions at encounter date** — condition SNOMED codes map to specialty (secondary signal)
3. **Encounter class** — `wellness`, `outpatient`, `inpatient`, `emergency` (context only)

Produce a specialty label per encounter using a SNOMED → specialty lookup table. Flag encounters where specialty cannot be derived as `unmapped_specialty` — these are excluded from the join.

**Output:** Specialty column added to `data/staging/synthea/encounters.parquet`

---

### Phase 6 — Join: Synthea Encounters to AGBonnet Notes

**Goal:** For each Synthea encounter, find the best-matching AGBonnet row and attach it.

**Join logic:**

**Step 1 — Hard filters (must pass both)**
```
synthea.specialty == agbonnet.predicted_specialty
synthea.age_band == agbonnet.age_band   (or agbonnet.age_band == "unknown")
```

This reduces the candidate pool to a manageable subset before scoring.

**Step 2 — Condition overlap score**

Normalize Synthea condition descriptions and AGBonnet condition strings to lowercase, remove stop words, and compute token overlap:

```
overlap_score = |synthea_conditions ∩ agbonnet_conditions| / |synthia_conditions ∪ agbonnet_conditions|
```

Simple Jaccard similarity on token sets. No embeddings needed.

**Step 3 — Sex compatibility bonus**
```
+0.10 if sex matches
 0.00 if either sex is unknown
-0.20 if sex conflicts
```

**Step 4 — Composite score**
```
composite = (0.70 × condition_overlap) + (0.30 × classifier_confidence) + sex_bonus
```

Classifier confidence is included to penalize low-confidence specialty classifications from being used as join anchors.

**Step 5 — Match selection**

| Composite score | Join confidence | Action |
|---|---|---|
| ≥ 0.70 | `high` | Accept match |
| 0.50–0.69 | `medium` | Accept match, flag in provenance |
| 0.30–0.49 | `low` | Use as fallback only if no better match exists |
| < 0.30 | `none` | Exclude encounter from corpus |

**Step 6 — Reuse budget**

Each AGBonnet row can be matched to at most **3 Synthea encounters** to prevent a single clinical note dominating the corpus. Track usage counts during join and deprioritize exhausted rows.

**Step 7 — Fallback**

If no AGBonnet row clears 0.30 for a given Synthea encounter, the encounter is excluded and flagged in `join_audit.jsonl` as `no_match`. Do not force a bad join.

**Outputs:**
- `data/staging/join_results.jsonl`
- `data/staging/join_audit.jsonl`

---

### Phase 7 — Curated Corpus Emission

**Goal:** Emit all final JSONL files with stable IDs, clean schemas, and full cross-references.

**Tasks:**
1. For each joined record, emit one row to each relevant output file
2. Write Synthea conditions, medications, procedures, observations per patient — these are longitudinal and not filtered to matched encounters
3. Write AGBonnet note and dialogue only for matched encounters
4. Assign stable zero-padded IDs across all entity types
5. Validate referential integrity — every foreign key must resolve
6. Write `manifest.json` with record counts, generation timestamp, and Synthea seed

**Referential integrity checks:**
- Every `encounter_id` in notes/dialogues/conditions/medications/procedures/observations exists in encounters
- Every `patient_id` in encounters exists in patients
- Every `agbonnet_source_row_id` in notes exists in join_results
- No orphaned records in any file

**Outputs:** All files under `data/clinical_corpus/`

---

### Phase 8 — Dataset Audit

**Goal:** Prove the corpus is coherent and ready for Scribe-IQ before the app is built.

**Audit metrics:**

| Category | Metrics |
|---|---|
| **Scale** | Patients · Encounters · Notes · Dialogues · Conditions · Medications · Procedures · Observations |
| **Join quality** | High/medium/low/no-match counts · Mean composite score · Fallback rate · Reuse distribution |
| **Coverage** | % of Synthea encounters with attached note · % excluded |
| **Specialty** | Distribution across corpus · Matches vs source |
| **Demographics** | Age band distribution · Sex distribution · Ethnicity distribution |
| **Longitudinality** | Encounters per patient (p25/p50/p75/max) · Date range span · Patients with ≥ 3 encounters |
| **Quality** | AGBonnet quality tier distribution · Low confidence join count |
| **Conditions** | Total unique conditions · Top 20 conditions · Mean conditions per patient |
| **Medications** | Total unique medications · Top 20 medications · Mean active meds per patient |

**Outputs:**
- `data/clinical_corpus/audit_report.md`
- `data/clinical_corpus/manifest.json`
- `data/clinical_corpus/dataset_card.md`

---

### Phase 9 — Downstream App Readiness

Scribe-IQ reads exclusively from `data/clinical_corpus/`. The application layer workflow:

**Pre-meeting summary**
```
patient_id
  → patients.jsonl          (demographics, primary specialty)
  → encounters.jsonl        (full encounter history, sorted by date)
  → conditions.jsonl        (active + historical conditions)
  → medications.jsonl       (current + historical medications)
  → observations.jsonl      (recent labs and vitals)
  → notes.jsonl             (reference notes from prior visits)
  → LLM prompt              (generate pre-meeting summary)
```

**Note generation**
```
encounter_id
  → notes.jsonl             (reference note for this encounter)
  → dialogues.jsonl         (conversation for this encounter)
  → LLM prompt              (generate clinical note from dialogue)
```

**Transcription demo**
```
encounter_id
  → dialogues.jsonl         (conversation text to drive transcription UI)
```

---

## 8. Repository Layout

```
scribe-iq/
  lakehouse/
    README.md
    requirements.txt
    scripts/
      validate_dataset.py           # L0  ✅
      stage_dataset.py              # L0  ✅
      classify_specialties.py       # L1  ✅
      export_staged_parquet_jsonl.py # optional export ✅
      create_seed_plan.py           # interim app seed ✅
      extract_join_keys.py          # Phase 2 (proposal)
      tier_quality.py               # Phase 3
      generate_synthea.sh           # Phase 4
      stage_synthea.py              # Phase 4
      map_synthea_specialties.py    # Phase 5
      join_encounters.py            # Phase 6
      build_corpus.py               # Phase 7
      audit_corpus.py               # Phase 8
    snomed_specialty_map.json       # Phase 5 (future)
  data/
    raw/                              # future: immutable HF + Synthea drops
    staging/                          # today: AGBonnet manifest + parquet + JSONL
      manifest.json
      AGBonnet__augmented-clinical-notes/
        train.parquet
        train.jsonl                   # optional export (large; often gitignored)
      specialty_predictions.jsonl
      specialty_prediction_summary.json
      phase1_seed_plan.json           # interim seed bundle
      patient_assignments.jsonl
      selected_note_records.jsonl
      agbonnet/                       # future normalized layout (join keys, tiers)
      synthea/                        # future
      join_results.jsonl              # future
      join_audit.jsonl                # future (staging-level)
    clinical_corpus/                  # future handoff to Project A
  reference-docs/
    CLINICAL_LAKEHOUSE_PROPOSAL_V2.md  ← this document
  roadmap/
    PHASE1_MASTER_PLAN.md              # Project A (app MVP) master plan
  backend/        # Project A — create after lakehouse handoff
  frontend/
```

---

## 9. Explicit Non-Goals

- No real patient data — entirely synthetic and semi-synthetic throughout
- No Azure OpenAI or cloud LLM calls in the pipeline
- No PostgreSQL or any relational database
- No vector database or embedding generation
- No semantic similarity for the join — Jaccard on token sets is sufficient
- No clinical validation by medical professionals
- No HIPAA compliance requirements
- No backend server or REST API
- No frontend or UI
- No RAG application — that is Scribe-IQ, built on top of this

---

## 10. Success Criteria

The lakehouse is complete when all of the following are true:

- [ ] AGBonnet join keys extracted for all 30,000 rows
- [ ] AGBonnet quality tiers assigned
- [ ] Synthea population generated with fixed seed and documented parameters
- [ ] Synthea data staged and validated in parquet
- [ ] Synthea encounters labeled with specialty
- [ ] Join produces high/medium confidence matches for ≥ 70% of Synthea encounters
- [ ] No AGBonnet row used more than 3 times
- [ ] All curated JSONL files emitted with stable cross-referenced IDs
- [ ] Referential integrity validated — zero orphaned records
- [ ] Audit report documents join quality, specialty, demographic, and entity distributions
- [ ] Dataset card documents both source datasets, join method, and known limitations
- [ ] Scribe-IQ can construct a coherent pre-meeting summary for any patient in the corpus using only `data/clinical_corpus/`

---

## 11. Known Limitations (to be documented in dataset card)

- AGBonnet dialogues are GPT-3.5 generated and do not reflect real clinical conversations
- AGBonnet summaries were generated from truncated notes — some clinical detail is only recoverable from `full_note`
- Condition matching uses token overlap, not semantic similarity — some clinically equivalent conditions may not score well
- Synthea conditions use SNOMED codes — AGBonnet conditions are free text. The join operates on normalized descriptions, not codes
- Dentistry rows in AGBonnet may reflect classifier misfire on oral surgery cases — spot-check recommended before demo
- The corpus is entirely synthetic. It must not be used for clinical decision support, clinical training, or any real patient care context

---

## 12. Final Framing

> **AGBonnet gives you language. Synthea gives you patients. The lakehouse gives you both.**

Scribe-IQ needs a corpus where a clinician can walk into a room and the system knows who the patient is, what their history looks like, and what this visit is probably about. That requires longitudinal structure Synthea provides and clinical realism AGBonnet provides. Neither dataset alone is sufficient. The join is the product.

Build the lakehouse. Build Scribe-IQ on top of it.

---

*Scribe-IQ Clinical Lakehouse · v2.0 · Revised proposal incorporating Synthea patient spine*
