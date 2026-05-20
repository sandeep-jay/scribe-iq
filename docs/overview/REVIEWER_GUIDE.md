# Reviewer Guide

This guide routes reviewers to the right deeper read in about 90 seconds. It does not replace the product narrative in [Portfolio Case Study](PORTFOLIO_CASE_STUDY.md).

## 90-second read

Scribe IQ is a healthcare AI platform prototype built on synthetic data only. It demonstrates:

- an offline synthetic clinical corpus pipeline ([Corpus Artifacts](../guides/CORPUS_ARTIFACTS.md)),
- a Postgres/pgvector serving layer ([System Overview](SYSTEM_OVERVIEW.md)),
- provider-agnostic LLM and embedding integrations ([Provider Guide](../guides/LLM_AND_EMBEDDING_PROVIDERS.md)),
- clinical documentation workflows ([Portfolio Case Study](PORTFOLIO_CASE_STUDY.md)),
- Responsible AI audit surfaces ([Privacy and Provider Boundaries](PRIVACY_AND_PROVIDER_BOUNDARIES.md)).

The project does not claim PHI readiness or production clinical deployment.

## What to look for

| Signal | Where |
|---|---|
| Healthcare product thinking | Patient chart, encounter viewer, pre-meeting prep, note generation in [Portfolio Case Study](PORTFOLIO_CASE_STUDY.md) |
| Data platform thinking | `data_prep/`, generated corpus artifact, dataset card, audit report in [Corpus Artifacts](../guides/CORPUS_ARTIFACTS.md) |
| AI engineering | Grounded RAG, embeddings, provider abstractions in [System Overview](SYSTEM_OVERVIEW.md) |
| Responsible AI | `ai_interactions`, redaction, citations, audit dashboard in [Privacy and Provider Boundaries](PRIVACY_AND_PROVIDER_BOUNDARIES.md) |
| Production judgment | Deferred SSO, tenancy, BAA, PHI controls in [Product Context](PRODUCT_CONTEXT.md) |

## Education-to-healthcare bridge

My background is in governed education data platforms: longitudinal student records, advising notes, privacy-sensitive analytics, and AI decision support. Scribe IQ translates that architecture into a healthcare-shaped system: longitudinal patient records, clinical notes, grounded retrieval, auditability, and human review boundaries. The deeper narrative is in [Portfolio Case Study](PORTFOLIO_CASE_STUDY.md).

## Role alignment

Scribe IQ demonstrates platform architecture, AI engineering, and Responsible AI work expected from:

- Lead Data & AI Platform Architect
- Lead AI Engineer
- AI/ML Platform Architect
- Healthcare / academic medical center data architect
- Responsible AI / GenAI platform engineer

## Suggested review paths

### Recruiter / hiring manager

1. [README](../../README.md)
2. [Portfolio Case Study](PORTFOLIO_CASE_STUDY.md)
3. [Resume Snippets](RESUME_SNIPPETS.md)

### Technical architect

1. [System Overview](SYSTEM_OVERVIEW.md)
2. [Design Notes](DESIGN_NOTES.md)
3. [Implemented Baseline](../architecture/IMPLEMENTED_BASELINE.md)
4. [Corpus Artifacts](../guides/CORPUS_ARTIFACTS.md)

### Data platform reviewer

1. [Corpus Artifacts](../guides/CORPUS_ARTIFACTS.md)
2. [`data_prep/README.md`](../../data_prep/README.md)
3. [Corpus pipeline reference](../reference/corpus_offline_pipeline_v2_brief.md)

## What this is not

- Not a production clinical system.
- Not PHI-ready.
- Not a packaged SaaS app.
- Not just a chatbot.
- Not dependent on real patient data.
