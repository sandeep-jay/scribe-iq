# Design notes

This document is the builder's perspective on what was decided, what was considered, and what was learned. It is written in first person because design judgement is not anonymous — it belongs to the person making the calls.

---

## Why this problem

Clinical documentation AI is a useful problem for a system like this because it forces the right constraints out into the open: hallucination is unacceptable, traceability is required, and the data substrate is messy and structured at the same time. Most LLM-app problems do not impose these constraints; once you take them seriously, you cannot build the same shapes you would for a generic chat-over-docs system.

I wanted a project where governance and grounding could not be optional add-ons. Choosing a clinical-shaped problem made that automatic.

---

## Decisions and the alternatives considered

### pgvector over Pinecone, Qdrant, or Weaviate

**The decision.** Use Postgres pgvector for embeddings, on the same instance that holds patients and notes.

**What I considered.** A managed vector store (Pinecone) would have been faster to set up for a flat retrieval use case. Qdrant or Weaviate self-hosted would have been more idiomatic for "RAG demo" framing. Both would have given better recall benchmarks for very large corpora.

**Why this won.** Two stores means two transactional models, two failure modes, two deployment surfaces, and two consistency stories. For a 50-patient corpus where retrieval quality is bounded by note length and structure anyway, the consistency win — embeddings join cleanly to the rows that produced them — matters more than peak retrieval throughput. The system would need an order of magnitude more data before a separate vector store earned its operational cost. At that point the abstraction in `app/embeddings.py` makes the swap mechanical.

### Citation contract in the prompt, not as a verifier

**The decision.** The chat system prompt requires the model to answer only from provided excerpts and to cite as `[note:uuid]`. There is no post-hoc verifier agent.

**What I considered.** A second LLM call that checks the first answer against the source documents — a common pattern in production RAG systems. More robust, theoretically.

**Why this won.** A verifier doubles latency and cost on the most expensive route in the system. For grounded RAG over a moderate-size corpus, putting the retrieval directly into the prompt and binding the model to citation syntax is the cheap, reliable answer. The verifier pattern earns its cost when answers span many documents or require multi-hop reasoning — neither of which is the demo's use case. The audit row captures what was retrieved and what was generated; that gives the post-hoc visibility a verifier would have provided, without doubling every call.

### Audit table as a first-class migration

**The decision.** `ai_interactions` is in the schema alongside `patients` and `notes`. AI-touching routes call `insert_ai_interaction` on the **request path** (a pool connection acquire, append-only `INSERT`, then return) — not via a separate async queue.

**What I considered.** Async logging to a queue or external observability platform (Datadog, custom OpenTelemetry sink). Lower latency overhead, cleaner separation.

**Why this won.** A queue introduces drift between the action and the audit record. If the queue fails or the consumer lags, the audit lags or is lost. For a governance-shaped system, the audit is part of the action — not telemetry about it. Writing it inline forces the design to take audit seriously: redaction, hashing, and the governance JSON shape are all properties of the response path, not of an observability sidecar that could be missing in dev.

The cost is a small write per AI call. The benefit is that the row reflects what happened on that HTTP request before the response completes (same operational window as the user-visible result, without claiming a single multi-statement DB transaction across unrelated earlier reads).

### Corpus build offline, not on demand

**The decision.** The application never invokes Synthea, the note pool, or the data-prep pipeline at request time. The corpus is built ahead of time, validated, and loaded as a single artifact.

**What I considered.** A live regeneration mode that lets a user request a new patient with new conditions on demand. This is a common demo pattern and visually impressive.

**Why this won.** Conflating data production with data serving makes both harder. The data-prep pipeline takes 30 minutes end-to-end with quality gates and a validation report. Running it inline means timeouts, partial states, and a much messier audit story. Separating the two means the application has a stable substrate to demonstrate against, and the pipeline can be improved without touching the request path.

### Optional features fail visibly

**The decision.** Without configured embeddings and an embeddings load, chat returns 503 with a specific message. Without a configured LLM provider, meeting prep returns a placeholder. The frontend reads `GET /health` and surfaces these states explicitly.

**What I considered.** A degraded silent path that hides unconfigured features entirely.

**Why this won.** A feature that is silently absent looks like a bug. A feature that is explicitly disabled with a clear message looks like configuration. The cost is one extra response shape per route; the benefit is that anyone running the system understands what they are seeing without reading documentation. This also means the same code path works in CI (most features unconfigured) and in a demo environment (most features on).

---

## Things that were not obvious

**Meeting-prep caching with fingerprint invalidation.** The first version regenerated the summary on every request. The second cached forever. Neither is right. The current design caches the generated text in `patient_meeting_prep` keyed by patient ID, but invalidates when the underlying note set changes — captured as a fingerprint hash of the note IDs and updated timestamps that fed the summary. This gives instant repeat reads without serving stale narrative when new notes arrive. The fingerprint is the cheap insurance against the "summary is from before the latest visit" failure mode.

**Audit on failure paths.** It would have been easier to record an `ai_interaction` only on successful responses. That is also wrong. Failed LLM calls, retrieval failures, and safety-check rejections are exactly the events governance needs to see. The audit code is structured to record interaction rows with a `status` field — `succeeded`, `failed`, `rejected` — so the table tells a full story, not a curated highlight reel.

**The corpus pipeline's 0.5 and 6.5 scripts.** Two scripts have decimal numbers (`05.5_extract_longitudinal_context.py`, `06.5_verify_aci_coverage.py`). They were inserted between the original integer steps when the design caught the need for longitudinal context propagation and reservation coverage verification. The decimal naming preserves the original numbering and makes the insertion legible — a small, deliberate signal that the pipeline evolved under review rather than being designed perfectly the first time.

---

## What I would change with a real production constraint

These are the calls that would change if the system were leaving the demonstration tier.

**Identity and tenancy.** `OptionalApiKeyMiddleware` is correct for what it is and wrong for production. SSO with org-scoped tokens, per-tenant DB isolation (either schema-per-tenant or row-level security on the `domain` field), and an audit binding from interaction rows to authenticated principals would all be required. None of this changes the route handlers; it replaces the middleware and adds an auth-context dependency.

**Embeddings strategy.** OpenAI `text-embedding-3-small` is fine for this scale. For real clinical corpora I would benchmark domain-specific embeddings (BGE-M3, MedCPT) and likely move to a hybrid retrieval design — BM25 plus dense — with reranking. The provider abstraction already exists; the work is in the retrieval pipeline.

**LLM provider and prompt versioning.** Fast demo providers are useful for iteration; for production I would want a primary plus a verified fallback approved by the institution, and prompt versions pinned per route with their hashes recorded in `ai_interactions` — which the schema already supports — rather than treated as code constants.

**Observability beyond the audit row.** The audit table is a complete record of AI behavior. It is not a complete record of system health. I would add OpenTelemetry traces for the FastAPI handlers, a metrics surface for latency and error rates by route, and structured log aggregation. The `X-Request-ID` propagation is already in place; this is mostly wiring.

**Agentic chat, when it earns its complexity.** The single-shot RAG path is the correct baseline. Tool-using chat — `search_notes`, `get_encounter`, `get_patient_summary` as model-callable functions — becomes valuable when users ask questions that span multiple retrievals or need structured patient facts. The audit schema already accommodates per-step records via the JSONB governance blob. I would add this behind a feature flag and benchmark the latency cost honestly.

---

## What this build is meant to prove

That a system can be built end-to-end — data pipeline, persistence, service layer, UI, governance — with documentation that holds up to architect review, and with the architectural restraint to know what to leave out. The deferred list is as deliberate as the built list. Both are signals about how the system was thought through.
