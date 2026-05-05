# Scribe-IQ Implementation Guide
**AI-Powered Clinical Documentation Demo**

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [Database Schema](#database-schema)
6. [UI/UX Design Specifications](#uiux-design-specifications)
7. [Data Integration](#data-integration)
8. [Implementation Tasks](#implementation-tasks)
9. [Testing Strategy](#testing-strategy)
10. [Deployment](#deployment)

---

## Project Overview

### Purpose
Scribe-IQ is a demonstration application showcasing AI-powered clinical documentation that:
- Converts doctor-patient conversations into structured SOAP notes
- Provides pre-visit patient summaries using AI
- Displays longitudinal patient data with trend visualizations
- Simulates real-time note generation during encounters

### Key Features
- ✅ **Patient List Dashboard** - Overview of all patients with trend indicators
- ✅ **Patient Detail View** - Comprehensive patient history, vitals, trends, timeline
- ✅ **Encounter Viewer** - Real-time conversation transcription and SOAP note generation
- ✅ **AI Pre-Meeting Summaries** - Synthesized patient context before visits
- ✅ **Timeline Visualization** - Interactive 3-year patient journey
- ✅ **Trend Analytics** - HbA1c, BP, LDL tracking with visual indicators

### Demo Constraints
- **Read-only**: No actual data persistence (simulated writes)
- **Local/Mock AI**: Uses Claude API with mock streaming for demo effect
- **Static Dataset**: 19 patients with 269 encounters (Synthea + custom data)

---

## Tech Stack

### Frontend
```
Framework:     Next.js 15 (App Router)
Language:      TypeScript
Styling:       Tailwind CSS
State:         React Context + Hooks (no Redux needed for demo)
UI Library:    Headless UI (for modals, dropdowns)
Icons:         Heroicons
```

### Backend
```
Framework:     FastAPI (Python)
Language:      Python 3.11+
AI:            Anthropic Claude API (claude-sonnet-4-20250514)
Database:      SQLite (read-only, pre-populated)
ORM:           SQLAlchemy
Validation:    Pydantic
```

### Data
```
Source:        Synthea synthetic patient data + custom encounters
Format:        FHIR-compliant JSON + custom SOAP notes
Storage:       SQLite database (patients.db)
```

---

## Frontend Architecture

### File Structure
```
scribe-iq-frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout
│   │   ├── page.tsx                   # Login page
│   │   ├── patients/
│   │   │   ├── page.tsx               # Patient list
│   │   │   └── [id]/
│   │   │       ├── page.tsx           # Patient detail
│   │   │       └── encounter/
│   │   │           └── page.tsx       # Encounter viewer
│   │   └── globals.css                # Tailwind + custom styles
│   ├── components/
│   │   ├── PatientList/
│   │   │   ├── PatientTable.tsx
│   │   │   ├── StatCards.tsx
│   │   │   └── SearchFilters.tsx
│   │   ├── PatientDetail/
│   │   │   ├── PatientHeader.tsx
│   │   │   ├── TrendCards.tsx
│   │   │   ├── AISummary.tsx
│   │   │   ├── Timeline.tsx
│   │   │   └── RecentNotes.tsx
│   │   ├── Encounter/
│   │   │   ├── PlaybackControls.tsx
│   │   │   ├── DialoguePanel.tsx
│   │   │   ├── SOAPNotePanel.tsx
│   │   │   └── ActionButtons.tsx
│   │   └── shared/
│   │       ├── Avatar.tsx
│   │       ├── Badge.tsx
│   │       ├── Button.tsx
│   │       └── TrendIndicator.tsx
│   ├── lib/
│   │   ├── api.ts                     # API client
│   │   ├── types.ts                   # TypeScript interfaces
│   │   └── utils.ts                   # Utility functions
│   └── public/
│       └── logo.svg
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### Key Components

#### 1. Patient List (`/patients`)
**Components:**
- `StatCards` - 4 metric cards (Total Patients, Encounters, Avg HbA1c, BP Control)
- `PatientTable` - Sortable table with avatars, trends, specialty badges
- `SearchFilters` - Search bar + filter buttons

**State:**
```typescript
interface PatientListState {
  patients: Patient[];
  stats: DashboardStats;
  filters: FilterState;
  searchQuery: string;
}
```

#### 2. Patient Detail (`/patients/[id]`)
**Components:**
- `PatientHeader` - Name, demographics, current vitals, conditions
- `TrendCards` - HbA1c, BP, LDL with trend indicators
- `AISummary` - Claude-generated pre-meeting summary
- `Timeline` - Interactive 14-encounter timeline with tooltips
- `RecentNotes` - Last 3 encounter notes with snippets

**State:**
```typescript
interface PatientDetailState {
  patient: Patient;
  vitals: Vitals;
  trends: TrendData;
  encounters: Encounter[];
  aiSummary: string;
}
```

#### 3. Encounter Viewer (`/patients/[id]/encounter`)
**Components:**
- `PlaybackControls` - Play/pause, progress bar, speed control
- `DialoguePanel` - Streaming conversation (doctor/patient messages)
- `SOAPNotePanel` - Real-time SOAP note generation with section status
- `ActionButtons` - Copy, Save, Edit

**State:**
```typescript
interface EncounterState {
  isPlaying: boolean;
  progress: number;
  dialogue: Message[];
  soapNote: SOAPNote;
  generationStatus: SectionStatus;
}
```

### Routing
```
/                           → Login page (demo auth)
/patients                   → Patient list dashboard
/patients/[id]              → Patient detail view
/patients/[id]/encounter    → Encounter viewer
```

### TypeScript Interfaces
```typescript
// Core types
interface Patient {
  id: string;
  mrn: string;
  name: string;
  age: number;
  gender: string;
  dob: string;
  specialty: 'Cardiology' | 'Endocrinology' | 'Pulmonology';
  conditions: string[];
  totalVisits: number;
}

interface Vitals {
  bp: string;
  hr: number;
  temp: number;
  timestamp: string;
}

interface TrendData {
  hba1c: { current: number; previous: number; change: number };
  bloodPressure: { current: string; previous: string; systolic: number };
  ldl: { current: number; goal: number };
}

interface Encounter {
  id: string;
  date: string;
  type: string;
  chiefComplaint: string;
  provider: string;
  snippet: string;
  fullNote?: SOAPNote;
}

interface SOAPNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

interface Message {
  speaker: 'Doctor' | 'Patient';
  text: string;
  timestamp: number;
}
```

---

## Backend Architecture

### API Endpoints

#### Authentication
```
POST /api/auth/login
Body: { username: string, password: string }
Response: { token: string, user: User }
Note: Demo only - hardcoded credentials (demo/demo)
```

#### Patients
```
GET /api/patients
Query: ?specialty=X&search=Y
Response: { patients: Patient[], stats: DashboardStats }

GET /api/patients/{patient_id}
Response: { patient: Patient, vitals: Vitals, trends: TrendData, encounters: Encounter[] }

GET /api/patients/{patient_id}/summary
Response: { summary: string }
Note: Calls Claude API to generate AI summary
```

#### Encounters
```
GET /api/encounters/{encounter_id}
Response: { encounter: Encounter, dialogue: Message[], soapNote: SOAPNote }

POST /api/encounters/{encounter_id}/stream
Response: SSE stream of dialogue + SOAP note generation
Note: Simulates real-time transcription and AI generation
```

### File Structure
```
scribe-iq-backend/
├── app/
│   ├── main.py                    # FastAPI app + CORS config
│   ├── routers/
│   │   ├── auth.py                # Authentication endpoints
│   │   ├── patients.py            # Patient CRUD
│   │   └── encounters.py          # Encounter + streaming
│   ├── models/
│   │   ├── patient.py             # SQLAlchemy Patient model
│   │   ├── encounter.py           # Encounter model
│   │   └── vitals.py              # Vitals model
│   ├── schemas/
│   │   ├── patient.py             # Pydantic schemas
│   │   └── encounter.py
│   ├── services/
│   │   ├── ai_service.py          # Claude API integration
│   │   ├── data_service.py        # Database queries
│   │   └── stream_service.py      # SSE streaming logic
│   ├── database.py                # SQLAlchemy setup
│   └── config.py                  # Environment config
├── data/
│   ├── patients.db                # SQLite database
│   ├── synthea_data/              # Raw Synthea FHIR files
│   └── scripts/
│       ├── import_synthea.py      # Synthea → SQLite
│       └── generate_encounters.py # Create SOAP notes
├── requirements.txt
└── .env.example
```

### AI Service Implementation
```python
# services/ai_service.py
import anthropic
from typing import AsyncGenerator

class AIService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    async def generate_summary(self, patient_data: dict) -> str:
        """Generate pre-meeting summary using Claude"""
        prompt = f"""You are a clinical AI assistant. Generate a concise pre-meeting summary for this patient:

Patient: {patient_data['name']}, {patient_data['age']}yo {patient_data['gender']}
Conditions: {', '.join(patient_data['conditions'])}
Recent encounters: {patient_data['recent_encounters']}

Provide:
1. Brief overview (1-2 sentences)
2. Recent history (key events from last 3 visits)
3. Lab trends (HbA1c, BP, cholesterol)
4. Medication changes

Keep it professional and concise (max 4 paragraphs)."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    async def stream_encounter(
        self, 
        dialogue: list[dict], 
        patient_context: dict
    ) -> AsyncGenerator[dict, None]:
        """Stream SOAP note generation as dialogue progresses"""
        # Implementation for real-time streaming
        # Yields: {"type": "dialogue" | "soap", "content": str, "section": str}
        pass
```

---

## Database Schema

### Tables

#### patients
```sql
CREATE TABLE patients (
    id TEXT PRIMARY KEY,
    mrn TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    dob DATE,
    specialty TEXT,
    conditions TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### encounters
```sql
CREATE TABLE encounters (
    id TEXT PRIMARY KEY,
    patient_id TEXT REFERENCES patients(id),
    date TIMESTAMP NOT NULL,
    type TEXT NOT NULL,
    chief_complaint TEXT,
    provider TEXT,
    subjective TEXT,
    objective TEXT,
    assessment TEXT,
    plan TEXT,
    dialogue TEXT, -- JSON array of messages
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### vitals
```sql
CREATE TABLE vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(id),
    encounter_id TEXT REFERENCES encounters(id),
    timestamp TIMESTAMP NOT NULL,
    systolic INTEGER,
    diastolic INTEGER,
    heart_rate INTEGER,
    temperature REAL,
    weight REAL,
    height REAL
);
```

#### labs
```sql
CREATE TABLE labs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(id),
    encounter_id TEXT REFERENCES encounters(id),
    date DATE NOT NULL,
    hba1c REAL,
    ldl REAL,
    hdl REAL,
    glucose REAL,
    creatinine REAL
);
```

### Sample Data (Patient: James Chen)
```sql
INSERT INTO patients VALUES (
    'pat_001',
    '847392',
    'James Chen',
    67,
    'M',
    '1957-03-15',
    'Cardiology',
    '["CAD", "Hypertension", "Type 2 Diabetes"]',
    '2022-06-01 00:00:00'
);

-- 14 encounters spanning 3 years
-- Most recent: Nov 15, 2024
INSERT INTO encounters VALUES (
    'enc_014',
    'pat_001',
    '2024-11-15 09:30:00',
    'Cardiology Follow-up',
    'Chest tightness',
    'Dr. Martinez',
    'Patient reports intermittent chest tightness with exertion...',
    'BP 138/84, HR 68, Stress test negative...',
    'CAD stable, HTN well-controlled, T2DM improving...',
    'Continue current medications. F/U 3 months.',
    '[{"speaker": "Doctor", "text": "Good morning..."}, ...]',
    '2024-11-15 10:15:00'
);
```

---

## UI/UX Design Specifications

### Design System

#### Colors
```css
/* Primary */
--primary-blue: #378ADD;
--primary-text: #1A1A1A;
--secondary-text: #666666;
--tertiary-text: #999999;

/* Backgrounds */
--bg-primary: #FFFFFF;
--bg-secondary: #F8F9FA;
--bg-tertiary: #F1F3F5;

/* Semantic */
--success: #639922;
--danger: #E24B4A;
--warning: #EF9F27;
--info: #378ADD;

/* Specialty Badges */
--cardiology: #378ADD;
--endocrinology: #EF9F27;
--pulmonology: #1D9E75;
```

#### Typography
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;

/* Headings */
h1: 24px / 500 weight
h2: 16px / 500 weight

/* Body */
body: 14px / 400 weight
small: 12px / 400 weight
caption: 11px / 400 weight (uppercase, 0.5px letter-spacing)
```

#### Spacing
```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 12px;
--spacing-lg: 16px;
--spacing-xl: 24px;
```

#### Border Radius
```css
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
```

### Screen Specifications

#### 1. Login Page
- **Layout**: Centered card (400px max-width)
- **Elements**:
  - Scribe-IQ logo + name
  - Tagline: "AI-Powered Clinical Documentation"
  - Username input (demo)
  - Password input (demo)
  - Sign In button (primary blue)
  - Footer: "Built with Next.js, FastAPI, and Claude AI"
- **Credentials**: demo/demo (hardcoded)

#### 2. Patient List Dashboard
- **Header**: "Patients" + subtitle with stats
- **Stat Cards** (4 columns):
  - Total Patients: 19
  - Active Encounters: 269
  - Avg HbA1c Improvement: -12%
  - BP Control Rate: 84%
- **Search/Filters**:
  - Search bar (icon left, placeholder: "Search by name, MRN, condition...")
  - Filter buttons: Specialty, Risk Level, Last Visit
- **Table Columns**:
  - Patient (avatar + name + MRN)
  - Age / Gender
  - Specialty (badge)
  - Visits (number)
  - Trends (arrow + metric)
  - Last Visit (date)
- **Interactions**:
  - Click row → Navigate to patient detail
  - Hover row → Light background highlight

#### 3. Patient Detail View
- **Section 1: Patient Header**
  - Name, age, demographics
  - Current vitals (BP, HR, Temp + timestamp)
  - Active condition badges
  - MRN, DOB, Specialty (right-aligned)

- **Section 2: Trend Cards** (3 columns)
  - HbA1c: Value + arrow + change
  - Blood Pressure: Value + arrow + change
  - LDL Cholesterol: Value + goal indicator

- **Section 3: AI Summary**
  - "Pre-Meeting Summary" header + AI badge
  - Regenerate button (top-right)
  - 2-3 paragraphs of synthesized history

- **Section 4: Patient Journey Timeline**
  - Title: "Patient Journey (14 encounters over 3 years)"
  - Interactive horizontal timeline (6 dots shown)
  - Hover tooltips with encounter details
  - Dates, reasons, vitals in tooltips

- **Section 5: Start Encounter Button**
  - Full-width primary button
  - "▶ Start Today's Encounter"
  - Prominent placement after timeline

- **Section 6: Recent Clinical Notes**
  - Title: "Recent Clinical Notes"
  - 3 encounter cards:
    - Title + Date
    - Chief complaint + Provider
    - 2-line snippet
    - Hover effect
  - "View All 14 Encounters →" button

#### 4. Encounter Viewer (Split-Screen)
- **Header Bar**:
  - Patient info + encounter date/time
  - "✕ End Encounter" button (right)

- **Playback Controls Bar**:
  - Play/pause button (circle)
  - Progress bar (filled 45%)
  - Time display "0:42 / 1:32"
  - Speed control "1.0x"

- **Left Panel: Clinical Dialogue**
  - Header: "CLINICAL DIALOGUE" + "● Recording" badge
  - Scrollable message list
  - Speaker badges: Doctor (blue), Patient (green)
  - Message text (14px, 1.7 line-height)
  - Fade-in animation for new messages

- **Right Panel: SOAP Note**
  - Header: "SOAP NOTE" + "⚡ AI Generating" badge
  - 4 sections (S, O, A, P)
  - Section status badges:
    - ✓ Complete (green)
    - ⚡ Generating (blue)
    - Pending (gray)
  - Blinking cursor on generating section
  - Monospace font for note text

- **Action Buttons** (bottom of right panel):
  - 📋 Copy Note
  - 💾 Save to EHR
  - ✏️ Edit

---

## Data Integration

### Synthea Dataset

#### Source
- **Repository**: https://github.com/synthetichealth/synthea
- **Generate Command**:
  ```bash
  ./run_synthea -p 19 California "San Francisco"
  ```
- **Output**: 19 patients in FHIR format (JSON)

#### Files to Use
```
synthea/output/fhir/
├── Hospital*.json           # Encounters
├── Practitioner*.json       # Providers
├── Patient*.json            # Patient demographics
├── Observation*.json        # Vitals, labs
└── Condition*.json          # Diagnoses
```

#### Import Script
```python
# data/scripts/import_synthea.py
import json
import sqlite3
from pathlib import Path

def import_synthea_patients():
    """Import Synthea FHIR data into SQLite"""
    conn = sqlite3.connect('patients.db')
    
    # Read patient files
    patient_files = Path('synthea_data/fhir/').glob('Patient*.json')
    
    for file in patient_files:
        with open(file) as f:
            fhir_patient = json.load(f)
            
        # Extract patient data
        patient = {
            'id': fhir_patient['id'],
            'mrn': generate_mrn(),
            'name': get_name(fhir_patient),
            'age': calculate_age(fhir_patient['birthDate']),
            'gender': fhir_patient['gender'],
            'dob': fhir_patient['birthDate'],
            'specialty': assign_specialty(),  # Random assignment
            'conditions': get_conditions(fhir_patient['id'])
        }
        
        # Insert into database
        insert_patient(conn, patient)
    
    conn.commit()
    conn.close()

def get_conditions(patient_id):
    """Extract conditions from Condition resources"""
    condition_files = Path('synthea_data/fhir/').glob(f'Condition*{patient_id}*.json')
    conditions = []
    
    for file in condition_files:
        with open(file) as f:
            condition = json.load(f)
            conditions.append(condition['code']['text'])
    
    return json.dumps(conditions)
```

### Custom Dataset Enhancements

#### Generate Realistic Encounters
```python
# data/scripts/generate_encounters.py
import anthropic
import random
from datetime import datetime, timedelta

def generate_cardiology_encounter(patient, visit_num):
    """Generate realistic cardiology encounter using Claude"""
    client = anthropic.Anthropic()
    
    # Context for Claude
    context = f"""Generate a realistic cardiology follow-up encounter for:
Patient: {patient.name}, {patient.age}yo {patient.gender}
Conditions: {', '.join(patient.conditions)}
Visit #{visit_num} of 14 (spanning 3 years)
Previous visits: {get_previous_context(patient, visit_num)}

Generate:
1. Chief complaint (1 sentence)
2. SOAP note (realistic clinical documentation)
3. Dialogue between doctor and patient (8-12 exchanges)

Make it clinically realistic with specific vitals, labs, medications."""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": context}]
    )
    
    # Parse Claude's response into structured data
    encounter_data = parse_encounter_response(response.content[0].text)
    
    return {
        'id': f'enc_{visit_num:03d}',
        'patient_id': patient.id,
        'date': calculate_visit_date(visit_num),
        'type': 'Cardiology Follow-up',
        'chief_complaint': encounter_data['chief_complaint'],
        'provider': 'Dr. Martinez',
        'subjective': encounter_data['soap']['subjective'],
        'objective': encounter_data['soap']['objective'],
        'assessment': encounter_data['soap']['assessment'],
        'plan': encounter_data['soap']['plan'],
        'dialogue': json.dumps(encounter_data['dialogue'])
    }
```

#### Dataset Requirements

**19 Patients total:**
- 8 Cardiology (CAD, hypertension, CHF)
- 6 Endocrinology (Type 2 diabetes, thyroid)
- 5 Pulmonology (COPD, asthma)

**269 Encounters total:**
- Average 14 encounters per patient
- Spanning 3 years (June 2022 - Nov 2024)
- Mix of:
  - Initial visits
  - Follow-ups
  - Lab reviews
  - Procedures (echo, stress test, pulmonary function)

**Lab Trends (for trend cards):**
- HbA1c: 6 data points over 6 months
- Blood Pressure: 6 data points over 6 months
- LDL: 6 data points over 6 months

---

## Implementation Tasks

### Phase 1: Project Setup (2-3 hours)

**Task 1.1: Initialize Next.js Frontend**
```bash
npx create-next-app@latest scribe-iq-frontend --typescript --tailwind --app
cd scribe-iq-frontend
npm install @headlessui/react @heroicons/react
```
- Create folder structure (`components/`, `lib/`, etc.)
- Set up Tailwind config with custom colors
- Create `.env.local` for API URL

**Task 1.2: Initialize FastAPI Backend**
```bash
mkdir scribe-iq-backend && cd scribe-iq-backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install fastapi uvicorn anthropic sqlalchemy pydantic python-dotenv
```
- Create folder structure (`app/routers/`, `app/models/`, etc.)
- Set up `.env` with `ANTHROPIC_API_KEY`
- Initialize SQLite database

**Task 1.3: Database Setup**
```bash
cd data
sqlite3 patients.db < schema.sql
```
- Run Synthea to generate 19 patients
- Run import script: `python scripts/import_synthea.py`
- Run encounter generator: `python scripts/generate_encounters.py`
- Verify: `sqlite3 patients.db "SELECT COUNT(*) FROM patients;"`  → Should return 19

---

### Phase 2: Backend API (4-6 hours)

**Task 2.1: Core Models & Database**
- [ ] Create SQLAlchemy models (`models/patient.py`, `models/encounter.py`)
- [ ] Set up database connection (`database.py`)
- [ ] Create Pydantic schemas (`schemas/patient.py`)
- [ ] Test database queries in Python REPL

**Task 2.2: Authentication Endpoints**
- [ ] Implement `/api/auth/login` (hardcoded demo/demo)
- [ ] Return mock JWT token
- [ ] Test with curl/Postman

**Task 2.3: Patient Endpoints**
- [ ] `GET /api/patients` - List all patients with stats
- [ ] `GET /api/patients/{id}` - Get patient details
- [ ] `GET /api/patients/{id}/summary` - Generate AI summary
- [ ] Add search/filter logic
- [ ] Test all endpoints

**Task 2.4: Encounter Endpoints**
- [ ] `GET /api/encounters/{id}` - Get encounter details
- [ ] `POST /api/encounters/{id}/stream` - SSE streaming
- [ ] Implement simulated streaming logic
- [ ] Test streaming with curl

**Task 2.5: AI Service**
- [ ] Implement `AIService.generate_summary()`
- [ ] Implement `AIService.stream_encounter()`
- [ ] Test Claude API integration
- [ ] Handle rate limiting and errors

---

### Phase 3: Frontend Components (8-10 hours)

**Task 3.1: Shared Components**
- [ ] Create `Avatar.tsx` (initials in colored circle)
- [ ] Create `Badge.tsx` (specialty, condition, status badges)
- [ ] Create `Button.tsx` (primary, secondary variants)
- [ ] Create `TrendIndicator.tsx` (arrow + color)

**Task 3.2: Login Page**
- [ ] Create `/app/page.tsx`
- [ ] Add login form
- [ ] Implement demo authentication
- [ ] Redirect to `/patients` on success

**Task 3.3: Patient List**
- [ ] Create `/app/patients/page.tsx`
- [ ] Implement `StatCards` component
- [ ] Implement `PatientTable` component
- [ ] Add search and filter functionality
- [ ] Fetch data from API
- [ ] Add loading states

**Task 3.4: Patient Detail**
- [ ] Create `/app/patients/[id]/page.tsx`
- [ ] Implement `PatientHeader` component
- [ ] Implement `TrendCards` component
- [ ] Implement `AISummary` component (with regenerate)
- [ ] Implement `Timeline` component (with tooltips)
- [ ] Implement `RecentNotes` component
- [ ] Fetch all data from API
- [ ] Add loading/error states

**Task 3.5: Encounter Viewer**
- [ ] Create `/app/patients/[id]/encounter/page.tsx`
- [ ] Implement `PlaybackControls` component
- [ ] Implement `DialoguePanel` component
- [ ] Implement `SOAPNotePanel` component
- [ ] Implement SSE streaming client
- [ ] Add playback simulation logic
- [ ] Test streaming visualization

---

### Phase 4: Integration & Polish (4-6 hours)

**Task 4.1: API Integration**
- [ ] Create `lib/api.ts` with typed fetch functions
- [ ] Implement error handling
- [ ] Add loading states across all pages
- [ ] Test all data flows end-to-end

**Task 4.2: Styling & Responsiveness**
- [ ] Ensure all components match design specs
- [ ] Test on mobile (responsive tables)
- [ ] Add hover states and transitions
- [ ] Polish spacing and alignment

**Task 4.3: Demo Experience**
- [ ] Add "Demo Mode" indicator
- [ ] Implement simulated "Save" confirmations
- [ ] Add helpful tooltips
- [ ] Test full user journey (login → patient → encounter)

**Task 4.4: Documentation**
- [ ] Write README with setup instructions
- [ ] Document API endpoints
- [ ] Add code comments
- [ ] Create deployment guide

---

### Phase 5: Testing (2-3 hours)

**Task 5.1: Unit Tests**
- [ ] Test backend data service functions
- [ ] Test API endpoint responses
- [ ] Test frontend utility functions

**Task 5.2: Integration Tests**
- [ ] Test full patient list → detail → encounter flow
- [ ] Test AI summary generation
- [ ] Test streaming encounter simulation
- [ ] Test search and filtering

**Task 5.3: Manual QA**
- [ ] Test all 19 patients load correctly
- [ ] Verify trend calculations
- [ ] Test timeline interactions
- [ ] Verify SOAP note streaming
- [ ] Check responsive design

---

## Testing Strategy

### Backend Tests
```python
# tests/test_patients.py
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_get_patients():
    response = client.get("/api/patients")
    assert response.status_code == 200
    assert len(response.json()["patients"]) == 19

def test_get_patient_detail():
    response = client.get("/api/patients/pat_001")
    assert response.status_code == 200
    assert response.json()["patient"]["name"] == "James Chen"

def test_ai_summary_generation():
    response = client.get("/api/patients/pat_001/summary")
    assert response.status_code == 200
    assert len(response.json()["summary"]) > 100
```

### Frontend Tests
```typescript
// __tests__/PatientList.test.tsx
import { render, screen } from '@testing-library/react';
import PatientList from '@/app/patients/page';

test('displays dashboard stats', async () => {
  render(<PatientList />);
  expect(await screen.findByText('Total Patients')).toBeInTheDocument();
  expect(await screen.findByText('19')).toBeInTheDocument();
});

test('displays patient table', async () => {
  render(<PatientList />);
  expect(await screen.findByText('James Chen')).toBeInTheDocument();
});
```

---

## Deployment

### Local Development
```bash
# Terminal 1: Backend
cd scribe-iq-backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd scribe-iq-frontend
npm run dev

# Access: http://localhost:3000
```

### Production Deployment Options

#### Option 1: Vercel (Frontend) + Railway (Backend)
```bash
# Frontend
vercel --prod

# Backend
railway up
```

#### Option 2: Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./scribe-iq-backend
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
  
  frontend:
    build: ./scribe-iq-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

#### Option 3: Single VPS
```bash
# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip nodejs npm nginx

# Setup backend
cd /var/www/scribe-iq-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Setup frontend
cd /var/www/scribe-iq-frontend
npm install && npm run build
npm start &

# Configure nginx reverse proxy
sudo nano /etc/nginx/sites-available/scribe-iq
```

---

## Key Implementation Notes

### 1. Mock Streaming Effect
Since this is a demo, the "real-time" transcription is simulated:
```typescript
// Encounter playback simulation
const simulateStreaming = async () => {
  const dialogue = preloadedDialogue; // From API
  const soapNote = preloadedSOAP;     // From API
  
  // Gradually reveal pre-generated content
  for (let i = 0; i < dialogue.length; i++) {
    await sleep(2000); // 2 seconds per message
    setMessages(prev => [...prev, dialogue[i]]);
    
    // Update SOAP sections as dialogue progresses
    if (i === 3) updateSOAP('subjective', soapNote.subjective);
    if (i === 6) updateSOAP('objective', soapNote.objective);
    if (i === 9) updateSOAP('assessment', soapNote.assessment);
    if (i === 11) updateSOAP('plan', soapNote.plan);
  }
};
```

### 2. AI Summary Caching
Don't call Claude API every time - cache summaries:
```python
# Cache in database or in-memory
@lru_cache(maxsize=100)
def get_patient_summary(patient_id: str) -> str:
    # Check if summary exists in DB
    cached = db.query(Summary).filter_by(patient_id=patient_id).first()
    if cached and cached.created_at > datetime.now() - timedelta(hours=24):
        return cached.content
    
    # Generate new summary
    summary = ai_service.generate_summary(patient_data)
    
    # Cache it
    db.add(Summary(patient_id=patient_id, content=summary))
    db.commit()
    
    return summary
```

### 3. Dataset Realism
Make trends realistic:
```python
def generate_hba1c_trend(baseline=8.1, target=7.0):
    """Generate realistic HbA1c improvement over 6 months"""
    values = []
    current = baseline
    
    for month in range(6):
        # Gradual decrease with some variance
        decrease = random.uniform(0.1, 0.2)
        current = max(target, current - decrease)
        values.append(round(current, 1))
    
    return values  # [8.1, 7.9, 7.8, 7.5, 7.3, 7.2]
```

### 4. Error Handling
Handle Claude API failures gracefully:
```python
try:
    summary = await ai_service.generate_summary(patient_data)
except anthropic.APIError as e:
    # Fallback to template-based summary
    summary = generate_template_summary(patient_data)
    logger.error(f"Claude API error: {e}")
```

---

## Success Criteria

### Functional Requirements
- ✅ All 19 patients display correctly in list
- ✅ Patient detail shows accurate vitals, trends, timeline
- ✅ AI summaries generate successfully
- ✅ Encounter playback simulates real-time streaming
- ✅ SOAP notes display with section-by-section generation
- ✅ Search and filters work on patient list

### Performance Requirements
- ✅ Patient list loads in < 1 second
- ✅ Patient detail loads in < 2 seconds
- ✅ AI summary generates in < 5 seconds
- ✅ Encounter streaming feels smooth (no janky animations)

### UX Requirements
- ✅ Design matches mockups pixel-perfect
- ✅ Responsive on desktop (1920x1080, 1366x768)
- ✅ All interactions have hover states
- ✅ Loading states prevent blank screens
- ✅ Error states show helpful messages

---

## File Checklist

### Required Files to Create

#### Frontend
- [ ] `src/app/layout.tsx`
- [ ] `src/app/page.tsx` (Login)
- [ ] `src/app/patients/page.tsx`
- [ ] `src/app/patients/[id]/page.tsx`
- [ ] `src/app/patients/[id]/encounter/page.tsx`
- [ ] `src/components/shared/Avatar.tsx`
- [ ] `src/components/shared/Badge.tsx`
- [ ] `src/components/shared/Button.tsx`
- [ ] `src/lib/api.ts`
- [ ] `src/lib/types.ts`
- [ ] `tailwind.config.ts` (with custom colors)

#### Backend
- [ ] `app/main.py`
- [ ] `app/routers/auth.py`
- [ ] `app/routers/patients.py`
- [ ] `app/routers/encounters.py`
- [ ] `app/models/patient.py`
- [ ] `app/models/encounter.py`
- [ ] `app/services/ai_service.py`
- [ ] `app/services/data_service.py`
- [ ] `app/database.py`
- [ ] `requirements.txt`
- [ ] `.env.example`

#### Data
- [ ] `data/patients.db` (SQLite)
- [ ] `data/schema.sql`
- [ ] `data/scripts/import_synthea.py`
- [ ] `data/scripts/generate_encounters.py`

#### Documentation
- [ ] `README.md`
- [ ] `API_DOCS.md`
- [ ] `DEPLOYMENT.md`

---

## Next Steps for the Coding Agent

1. **Start with Phase 1** - Set up both projects
2. **Run database scripts** - Import Synthea data
3. **Build backend API first** - Test endpoints with curl
4. **Build frontend components** - Match design specs exactly
5. **Integrate and test** - End-to-end user flows
6. **Deploy** - Choose deployment option

**Estimated Total Time: 20-30 hours**

Good luck! 🚀
