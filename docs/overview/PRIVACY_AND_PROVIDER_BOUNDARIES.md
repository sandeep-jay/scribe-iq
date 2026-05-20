# Privacy and provider boundaries

## Demo corpus

Scribe-IQ ships with a **synthetic** clinical corpus for portfolio and local demos. Do not load real PHI into demo environments.

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
