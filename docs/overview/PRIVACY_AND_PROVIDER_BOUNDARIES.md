# Privacy and provider boundaries

## Demo corpus

Scribe-IQ ships with a **synthetic** clinical corpus for product walkthroughs and local demos. Do not load real PHI into demo environments.

## What leaves the deployment

When LLM features run, **selected prompt context** (system instructions, retrieved note excerpts, user messages, transcripts) is sent to the configured provider:

- **Groq** (default demo)
- **Azure OpenAI** (institution-controlled Azure deployment)
- **Amazon Bedrock** (AWS-native deployment)

Embeddings may use OpenAI, Azure OpenAI, or Amazon Bedrock separately (`EMBEDDING_PROVIDER`). Switching embedding providers requires re-embedding stored vectors because provider vector spaces are not interchangeable.

## Audit storage

The Responsible AI audit table stores **hashes** and **redacted previews** of inputs/outputs — not full prompt or completion bodies.

## Enterprise providers are not automatic PHI compliance

Azure OpenAI and Bedrock can run under stronger enterprise control postures (private networking, IAM/RBAC, institutional accounts). They **do not** by themselves make this application PHI-ready. Production use with PHI requires, at minimum:

- Institutional approval and appropriate agreements (e.g. BAA / vendor review)
- Private networking and egress controls where required
- SSO/RBAC, tenant isolation, retention and logging policies
- Formal de-identification and access controls

## Demo mode

Use synthetic data only. Do not point demo `.env` files at production patient systems or real identifiers.

---

## Provider modes

The same code paths run against three LLM provider postures and three embedding provider postures. Choose per deployment, not per request.

| Mode | LLM provider | Embedding provider | Typical posture |
|------|--------------|-------------------|-----------------|
| **Demo / local** | Groq (`LLM_PROVIDER=groq`) | OpenAI (`EMBEDDING_PROVIDER=openai`) | Local laptop, public cloud APIs, synthetic data only |
| **Institutional Azure** | Azure OpenAI (`LLM_PROVIDER=azure_openai`) | Azure OpenAI (`EMBEDDING_PROVIDER=azure_openai`) | Customer-controlled Azure tenancy, BAA-eligible deployment, private networking optional |
| **AWS-native** | Amazon Bedrock (`LLM_PROVIDER=bedrock`) | Amazon Bedrock (`EMBEDDING_PROVIDER=bedrock`) | Customer AWS account, IAM-scoped role/profile, VPC egress controls optional |
| **Mixed (advanced)** | Any of the above | Any of the above | E.g. Azure OpenAI for chat, OpenAI for embeddings — supported by the abstraction, but rare in practice |

For full environment variables and the embedding-rebuild workflow when switching modes, see [`docs/guides/LLM_AND_EMBEDDING_PROVIDERS.md`](../guides/LLM_AND_EMBEDDING_PROVIDERS.md).

---

## Embedding provider caveat

The embedding provider is part of the **data substrate**, not just a runtime knob. Three properties follow from this:

1. **Vector spaces are not interchangeable.** Switching `EMBEDDING_PROVIDER` (or even the embedding model within a provider) requires re-running `scribe-load-corpus --embed` against the same corpus artifact. Stored vectors from a different provider will produce nonsense retrieval.
2. **The rebuild is operational, not silent.** The supported workflow (clear stored embeddings, re-run loader, verify via `GET /health`) is documented and idempotent. The system does **not** auto-detect mismatches at query time and silently degrade; it returns explicit 503s when embeddings are absent and surfaces the provider in health.
3. **The embedding posture matters as much as the LLM posture.** The embedding provider sees the same note text the LLM provider does. A deployment that locks down the LLM provider but uses a different embedding posture has not actually locked down its data egress.

---

## Product interpretation

This repository is a **demonstration**, not a clinical product. The privacy posture should be read accordingly.

- **No PHI is involved.** The corpus is synthetic (Synthea + public note datasets, adapted), and the documentation states this everywhere a reader could plausibly assume otherwise. The product value is the *shape* of the privacy thinking, not a compliance claim.
- **The provider boundary is the load-bearing artifact, not the credentials.** What matters for evaluation is that the code separates LLM provider from embedding provider, that `GET /health` exposes the configured posture, that the audit table redacts content rather than mirrors it, and that switching providers is a deployment-level decision with explicit operational steps. Those are the design signals; the keys themselves are deliberately scoped to demo accounts.
- **Enterprise providers are not a compliance claim.** Azure OpenAI and Bedrock support stronger institutional postures, and the project documents how those postures plug in. The docs are explicit that this is necessary but not sufficient for PHI: BAA, SSO/RBAC, multi-tenant isolation, formal de-identification, retention policy, and observability are all called out as production deltas in [`DESIGN_NOTES.md`](./DESIGN_NOTES.md) and [`PORTFOLIO_CASE_STUDY.md`](./PORTFOLIO_CASE_STUDY.md).
- **Reviewers should look for restraint, not coverage.** The fact that the project says "synthetic only" and "not PHI-ready" out loud is itself the signal — a product prototype that overclaimed PHI readiness would be a worse signal than one that names the boundary plainly.
