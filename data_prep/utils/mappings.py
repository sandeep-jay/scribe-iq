import re

# SNOMED CT → ICD-10-CM (small fallback when NLM ExtendedMap is not installed)
SNOMED_TO_ICD10_FALLBACK = {
    "44054006": "E11.9",
    "46635009": "E10.9",
    "73595000": "E03.9",
    "55822004": "E78.5",
    "162864005": "E66.9",
    "237599002": "E66.01",
    "38341003": "I10",
    "59621000": "I10",
    "53741008": "I25.10",
    "49436004": "I48.91",
    "230690007": "I63.9",
    "195967001": "J45.909",
    "267102003": "J45.20",
    "703151001": "J45.51",
    "13645005": "J44.1",
    "233604007": "J15.9",
    "444814009": "J06.9",
    "40122008": "J18.9",
    "36971009": "J32.9",
    "43878008": "J02.9",
    "34000006": "K50.90",
    "15777000": "K21.0",
    "74400008": "K37",
    "64859006": "M81.0",
    "396275006": "M19.90",
    "69896004": "M06.9",
    "370143000": "M54.5",
    "40055000": "N18.3",
    "90688005": "N18.9",
    "9855000": "N40.1",
    "57870002": "N39.0",
    "11840006": "N20.0",
    "62106007": "N10",
    "84757009": "G40.909",
    "26929004": "G30.9",
    "35489007": "F32.9",
    "197480006": "F41.1",
    "415068001": "L40.0",
    "271737000": "D64.9",
    "93761005": "C18.9",
    "363346000": "C80.1",
    "195662009": "J06.9",
    "3928004": "H66.90",
    "50043002": "J96.00",
    "298705000": "M79.3",
}

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

MTSAMPLES_TO_STANDARD_SPECIALTY = {
    "Cardiovascular / Pulmonary": "Cardiology",
    "Neurology": "Neurology",
    "Orthopedic": "Orthopedics",
    "Gastroenterology": "Gastroenterology",
    "Urology": "Urology",
    "Nephrology": "Nephrology",
    "Psychiatry / Psychology": "Psychiatry",
    "Dermatology": "Dermatology",
    "Endocrinology": "Endocrinology",
    "Ophthalmology": "Ophthalmology",
    "ENT - Otolaryngology": "Otorhinolaryngology",
    "General Medicine": "General Medicine",
    "Obstetrics / Gynecology": "Obstetrics",
    "Pediatrics - Neonatal": "Pediatrics",
    "Rheumatology": "Orthopedics",
    "Hematology - Oncology": "Oncology",
    "Pulmonology": "Pulmonology",
    "SOAP / Chart / Progress Notes": "General Medicine",
    "Office Notes": "General Medicine",
    "Consult - History and Phy.": "General Medicine",
    "Pain Management": "Orthopedics",
    "Sleep Medicine": "Pulmonology",
    "Physical Medicine - Rehab": "Orthopedics",
    "Podiatry": "Orthopedics",
    "Allergy / Immunology": "Infectious Disease",
    "Chiropractic": "Orthopedics",
}

CC_TO_SPECIALTY = {
    (
        "chest", "cardiac", "heart", "palpitation", "angina", "coronary",
        "hypertension", "blood pressure",
    ): "Cardiology",
    (
        "seizure", "neuro", "headache", "migraine", "stroke", "memory",
        "tremor", "epilepsy", "dizziness",
    ): "Neurology",
    (
        "knee", "hip", "back pain", "joint", "fracture", "orthop",
        "shoulder", "bone", "arthritis", "spine",
    ): "Orthopedics",
    (
        "bowel", "abdominal", "crohn", "colitis", "gastro", "reflux",
        "diarrhea", "stomach", "colon",
    ): "Gastroenterology",
    (
        "breath", "asthma", "copd", "pulmon", "cough", "lung",
        "respiratory", "wheez",
    ): "Pulmonology",
    ("kidney", "renal", "dialysis", "ckd", "creatinine"): "Nephrology",
    ("skin", "rash", "dermat", "psoriasis", "eczema", "acne"): "Dermatology",
    (
        "diabetes", "thyroid", "endocrin", "glucose", "insulin",
        "a1c", "weight",
    ): "Endocrinology",
    (
        "depression", "anxiety", "psych", "bipolar", "mental",
        "mood", "panic",
    ): "Psychiatry",
    ("urin", "prostate", "bladder", "urolog", "incontinence"): "Urology",
    ("eye", "vision", "ophthalm", "cataract", "glaucoma"): "Ophthalmology",
    (
        "ear", "nose", "throat", "ent", "sinus", "hearing",
        "tonsil",
    ): "Otorhinolaryngology",
    (
        "pneumonia", "sepsis", "cellulitis", "infection", "bacteremia",
        "tuberculosis", "covid", "influenza", "urinary tract", "pyelonephritis", "cystitis",
    ): "Infectious Disease",
    (
        "cancer", "carcinoma", "malignant", "oncolog", "chemotherapy", "metastasis",
        "melanoma", "lymphoma", "tumor",
    ): "Oncology",
    ("well child", "well-baby", "neonatal", "newborn"): "Pediatrics",
}


def _keyword_clinical_match(keyword: str, blob: str) -> bool:
    """Match multi-word phrases as substring; single words use a word boundary (avoids `ear` matching inside `heart`)."""
    kw = keyword.strip().lower()
    if not kw:
        return False
    if " " in kw:
        return kw in blob
    return re.search(r"\b" + re.escape(kw) + r"\b", blob) is not None


def specialty_from_clinical_text(*parts: str | None) -> str | None:
    """Infer specialty from free-text phrases; no licensed terminologies required."""
    blob = " ".join(p.strip().lower() for p in parts if isinstance(p, str) and p.strip())
    if not blob:
        return None
    for keywords, specialty in CC_TO_SPECIALTY.items():
        if any(_keyword_clinical_match(kw, blob) for kw in keywords):
            return specialty
    return None
