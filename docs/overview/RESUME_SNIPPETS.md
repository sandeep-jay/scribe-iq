# Resume and LinkedIn snippets

Drop-in descriptions for resume bullets, healthcare-targeted variants, and LinkedIn-length copy. All variants describe the same project ([Scribe IQ portfolio case study](PORTFOLIO_CASE_STUDY.md)); pick the one that matches the audience.

---

## Generic engineering version (resume-bullet length)

**Scribe IQ — end-to-end grounded clinical documentation system.** Built a full-stack demonstration (Next.js + FastAPI + Postgres/pgvector) of retrieval-grounded LLM documentation with first-class governance: citation-contract RAG over a 50-patient synthetic corpus, append-only `ai_interactions` audit on the request path, configurable LLM and embedding providers (Groq, OpenAI, Azure OpenAI, Amazon Bedrock), and an offline nine-step data pipeline (Synthea + ACI-Bench + MTSamples → match → score → cohort → adapt → validate). Architected for restraint: synthetic data only, explicit deferred-list with named extension seams, audience-routed documentation, structured logging with `X-Request-ID` propagation, and pre-commit secret scanning.

---

## Healthcare / UCLA-targeted version

**Scribe IQ — grounded clinical documentation demonstration.** Designed and built an end-to-end clinical AI documentation system (Next.js, FastAPI, Postgres + pgvector) to demonstrate the architectural restraint and governance posture required for institutional healthcare AI. Treats hallucination as a safety failure rather than a usability bug: every chat answer is retrieval-grounded with a `[note:uuid]` citation contract enforced in the system prompt, every AI-touching route writes an append-only audit row to a first-class `ai_interactions` table on the request path, and provider boundaries (Groq demo, Azure OpenAI / Amazon Bedrock for institutional deployments) are stated explicitly with clear caveats that enterprise providers do not by themselves create PHI compliance. Bridges institutional data-system experience from higher-education (longitudinal records, governance as schema, multi-stakeholder views) into clinical-shaped systems. Synthetic corpus only; documentation names what would change for a production PHI deployment (SSO, multi-tenant isolation, BAA, formal de-identification, observability).

---

## Short LinkedIn version

Built **Scribe IQ**, an end-to-end grounded clinical documentation demo — Next.js + FastAPI + Postgres/pgvector with citation-contract RAG, first-class `ai_interactions` audit, and pluggable LLM/embedding providers (Groq / OpenAI / Azure OpenAI / Amazon Bedrock). Synthetic data only; the goal is to show how I think about governance, provider boundaries, and what to leave out — not to ship a clinical product. Case study: [PORTFOLIO_CASE_STUDY.md](PORTFOLIO_CASE_STUDY.md).
