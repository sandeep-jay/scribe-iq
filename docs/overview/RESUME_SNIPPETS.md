# Resume and LinkedIn snippets

Drop-in descriptions for resume bullets, healthcare-targeted variants, and LinkedIn-length copy. All variants describe the same project ([Scribe IQ product case study](PORTFOLIO_CASE_STUDY.md)); pick the one that matches the audience.

---

## Generic engineering version (resume-bullet length)

**Scribe IQ — healthcare AI platform prototype.** Built an end-to-end demonstration of data-product style synthetic clinical corpus construction, governed AI serving, and clinical documentation workflows. The system separates offline corpus construction from runtime serving: a nine-step `data_prep/` pipeline builds a validated synthetic corpus artifact from Synthea and public clinical note sources; FastAPI/Postgres/pgvector serve patient charts, encounter views, grounded RAG chat with citations, structured note generation, and an `ai_interactions` audit dashboard. Pluggable LLM/embedding providers (Groq, OpenAI, Azure OpenAI, Amazon Bedrock); synthetic data only with explicit PHI, SSO, tenancy, and BAA caveats.

---

## Healthcare-targeted version

**Scribe IQ — grounded clinical documentation demonstration.** Designed and built an end-to-end clinical AI documentation system (Next.js, FastAPI, Postgres + pgvector) to demonstrate the architectural restraint and governance posture required for institutional healthcare AI. Treats hallucination as a safety failure rather than a usability bug: every chat answer is retrieval-grounded with a `[note:uuid]` citation contract enforced in the system prompt, audited AI paths write append-only rows to a first-class `ai_interactions` table with admin-visible `success`, `degraded`, `failed`, and `blocked` status aggregation, and provider boundaries (Groq demo, Azure OpenAI / Amazon Bedrock for institutional deployments) are stated explicitly with clear caveats that enterprise providers do not by themselves create PHI compliance. Bridges institutional data-system experience from higher-education (longitudinal records, governance as schema, multi-stakeholder views) into clinical-shaped systems. Synthetic corpus only; documentation names what would change for a production PHI deployment (SSO, multi-tenant isolation, BAA, formal de-identification, observability).

---

## Short LinkedIn version

Built **Scribe IQ**, an end-to-end grounded clinical documentation demo — Next.js + FastAPI + Postgres/pgvector with citation-contract RAG, first-class `ai_interactions` audit, and pluggable LLM/embedding providers (Groq / OpenAI / Azure OpenAI / Amazon Bedrock). Synthetic data only; the goal is to show how I think about governance, provider boundaries, and what to leave out — not to ship a clinical product. Case study: [PORTFOLIO_CASE_STUDY.md](PORTFOLIO_CASE_STUDY.md).
