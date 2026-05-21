# Target role alignment

Scribe IQ is one portfolio artifact. It should be read alongside adjacent work in campus RAG assistance and lakehouse / readmission-style data platform builds. This repository focuses on the healthcare-shaped AI product surface: clinical notes, chart review, grounded retrieval, note generation, provider boundaries, and Responsible AI auditability.

The target roles this repo supports tend to combine architecture leadership with hands-on delivery. Across academic health, university IT, research, advancement analytics, and education innovation roles, the repeated inspection pattern is:

- enterprise information and data architecture
- cloud-native and lakehouse platform judgment
- AI/ML and LLM system implementation
- RAG, vector search, agents, prompt/model governance, and MLOps awareness
- full-stack or API-oriented engineering
- DevOps, CI/CD, testing, observability, and reliability
- data governance, privacy, access boundaries, and regulated-environment judgment
- stakeholder communication, technical leadership, mentoring, and architecture documentation

Scribe IQ is intentionally scoped to demonstrate those patterns in a synthetic clinical documentation setting. It does not claim PHI readiness or production clinical validation.

---

## Role patterns this repository addresses

| Target role pattern | What reviewers are usually looking for | Where Scribe IQ provides evidence |
|---|---|---|
| Enterprise information / solution architect | A clear architecture blueprint for governed data access, AI readiness, interoperability, and risk-aware platform decisions | [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md), [`DESIGN_NOTES.md`](DESIGN_NOTES.md), [`PRIVACY_AND_PROVIDER_BOUNDARIES.md`](PRIVACY_AND_PROVIDER_BOUNDARIES.md) |
| Healthcare data / AI platform architect | Healthcare-shaped workflows, synthetic-data discipline, provider egress clarity, auditability, and production deltas for PHI / SSO / tenancy | [`PORTFOLIO_CASE_STUDY.md`](PORTFOLIO_CASE_STUDY.md), [`PRIVACY_AND_PROVIDER_BOUNDARIES.md`](PRIVACY_AND_PROVIDER_BOUNDARIES.md), [`../architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md) |
| Education IT / innovation software architect | Full-stack product architecture, cloud-native service boundaries, REST APIs, DevOps practices, LLM/lakehouse awareness, and architecture documentation | [`../../frontend/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/frontend/README.md), [`../../backend/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/README.md), [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) |
| AI engineer / GenAI platform engineer | RAG, embeddings, prompt contracts, provider abstraction, audit logging, degraded states, and clear extension seams for agents/evals | [`../../backend/app/api/chat.py`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/app/api/chat.py), [`../../backend/app/llm/`](https://github.com/sandeep-jay/scribe-iq/tree/main/backend/app/llm/), [`../../backend/app/embeddings/`](https://github.com/sandeep-jay/scribe-iq/tree/main/backend/app/embeddings/), [`DESIGN_NOTES.md`](DESIGN_NOTES.md) |
| Data science / analytics director | Structured and unstructured data thinking, reproducible corpus construction, predictive/ML-adjacent architecture, stakeholder-readable documentation | [`../guides/CORPUS_ARTIFACTS.md`](../guides/CORPUS_ARTIFACTS.md), [`../../data_prep/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data_prep/README.md), [`PORTFOLIO_CASE_STUDY.md`](PORTFOLIO_CASE_STUDY.md) |
| Software architect / engineering lead | Architecture tradeoffs, full-stack implementation, code review surfaces, platform reliability thinking, and explicit technical debt / production deltas | [`DESIGN_NOTES.md`](DESIGN_NOTES.md), [`../architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md), [`../roadmap/SCRIBE_IQ_UI_ROADMAP.md`](../roadmap/SCRIBE_IQ_UI_ROADMAP.md) |

---

## Architecture claims and evidence

| Claim | Evidence in this repo |
|---|---|
| Grounded RAG over clinical notes | [`backend/app/api/chat.py`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/app/api/chat.py) retrieves note embeddings, builds citation-shaped prompt blocks, and returns citations. |
| AI audit is first-class data | [`backend/alembic/versions/20260505_003_ai_interactions.py`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/alembic/versions/20260505_003_ai_interactions.py) creates `ai_interactions`; [`backend/app/responsible_ai/`](https://github.com/sandeep-jay/scribe-iq/tree/main/backend/app/responsible_ai/) handles hashes, redaction, source traces, and safety heuristics. |
| Provider boundaries are configurable | [`backend/app/config.py`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/app/config.py), [`backend/app/llm/`](https://github.com/sandeep-jay/scribe-iq/tree/main/backend/app/llm/), and [`backend/app/embeddings/`](https://github.com/sandeep-jay/scribe-iq/tree/main/backend/app/embeddings/) separate Groq, Azure OpenAI, OpenAI embeddings, and Amazon Bedrock postures. |
| Corpus build is a data product, not a fixture | [`data_prep/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data_prep/README.md) and [`docs/guides/CORPUS_ARTIFACTS.md`](../guides/CORPUS_ARTIFACTS.md) document the offline Synthea + public-note pipeline, validation, manifest, dataset card, and audit report. |
| Product UX is workflow-shaped | [`frontend/src/app/patients/`](https://github.com/sandeep-jay/scribe-iq/tree/main/frontend/src/app/patients/), [`frontend/src/app/chat/`](https://github.com/sandeep-jay/scribe-iq/tree/main/frontend/src/app/chat/), and screenshots in [`docs/assets/showcase/readme/`](../assets/showcase/readme/) show chart review, encounter viewing, meeting prep, note generation, and audit review. |
| Production limits are explicit | [`PRIVACY_AND_PROVIDER_BOUNDARIES.md`](PRIVACY_AND_PROVIDER_BOUNDARIES.md) and [`DESIGN_NOTES.md`](DESIGN_NOTES.md) name PHI, BAA, SSO/RBAC, tenancy, de-identification, observability, and clinical validation as production deltas. |

---

## How to read this repo for the target roles

Start with the README for the product shape. Then:

1. Read [`PORTFOLIO_CASE_STUDY.md`](PORTFOLIO_CASE_STUDY.md) to understand the education-to-healthcare bridge and product thesis.
2. Read [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) for the runtime and corpus architecture.
3. Read [`PRIVACY_AND_PROVIDER_BOUNDARIES.md`](PRIVACY_AND_PROVIDER_BOUNDARIES.md) to evaluate governance and provider egress discipline.
4. Inspect [`backend/app/api/chat.py`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/app/api/chat.py), [`backend/app/api/patients.py`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/app/api/patients.py), and [`backend/app/responsible_ai/`](https://github.com/sandeep-jay/scribe-iq/tree/main/backend/app/responsible_ai/) for the AI workflow implementation.
5. Inspect [`data_prep/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data_prep/README.md) if the review is about data engineering, reproducibility, or analytics/data-science platform judgment.

---

## Portfolio boundary

Scribe IQ should not carry every target-role signal by itself.

- Campus RAG assistance work is the stronger companion artifact for enterprise/university knowledge systems, agentic workflows, internal tool integration, and campus-wide GenAI enablement.
- Lakehouse / readmission-style Fabric work is the stronger companion artifact for Microsoft Fabric, Azure lakehouse, healthcare analytics, medallion architecture, and readmission/predictive-data workflows.
- Scribe IQ is the strongest artifact for healthcare-shaped AI product thinking, clinical-note grounding, provider-boundary design, Responsible AI auditability, and production-restraint documentation.

Together, those artifacts tell a broader story: governed institutional data platforms, AI-enabled applications, and cloud/lakehouse architecture across education, academic health, and research settings.
