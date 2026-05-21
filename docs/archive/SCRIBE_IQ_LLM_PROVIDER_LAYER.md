---
title: Scribe-IQ LLM provider layer
status: active
last_updated: 2026-05-19
---

# Scribe-IQ LLM provider layer

> **Archived (2026-05).** Preserved for design lineage. Current authoritative source: [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md). Map: [`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md).


Execution roadmap for a provider-agnostic LLM runtime (`groq`, `azure_openai`, `bedrock`) with consistent audit metadata.

## Goals

- Replace Groq-only helpers with `app.llm` package + factory.
- Preserve route HTTP contracts (`503` configuration, `502` upstream/validation).
- Record `model_provider` / `model_name` from completion results in `ai_interactions`.
- Config-only `/health` readiness (no live cloud credential checks).

## PR sequence

| PR | Branch | Scope |
|----|--------|--------|
| 1 | `feat/llm-provider-pr1-foundation` | Package skeleton, Groq provider, factory, exceptions, unit tests |
| 2 | `feat/llm-provider-pr2-routes-health` | Route wrappers, audit source, health capability fields |
| 3 | `feat/llm-provider-pr3-azure-docs` | Azure OpenAI provider, privacy doc, env/README |
| 4 | `feat/llm-provider-pr4-bedrock` | Bedrock provider, boto3, converter tests |

## Validation

```bash
cd backend && python -m pytest tests/ -q --ignore=tests/test_integration_db.py
```

## Related docs

- [PRIVACY_AND_PROVIDER_BOUNDARIES.md](../overview/PRIVACY_AND_PROVIDER_BOUNDARIES.md)
- [IMPLEMENTED_BASELINE.md](../architecture/IMPLEMENTED_BASELINE.md)
