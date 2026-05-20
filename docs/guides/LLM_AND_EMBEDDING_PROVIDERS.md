# LLM and embedding providers

## Purpose

Scribe IQ separates **LLM provider** (chat, pre-meeting summary, note generation) from **embedding provider** (vector encoding of notes for RAG). Both are configurable through environment variables read by the typed `Settings` layer; both are surfaced in `GET /health` so the frontend and operators can see exactly which capabilities are configured.

Pick the provider posture that matches the deployment:

- **Local demo:** `LLM_PROVIDER=groq` with `EMBEDDING_PROVIDER=openai` is the simplest path and what `QUICKSTART.md` assumes.
- **Institutional Azure tenancy:** `LLM_PROVIDER=azure_openai` and `EMBEDDING_PROVIDER=azure_openai`, pointing at your Azure deployment.
- **AWS-native deployment:** `LLM_PROVIDER=bedrock` and `EMBEDDING_PROVIDER=bedrock`, configured against your Bedrock account.

The provider choice is per-deployment, not per-request. Switching the LLM provider does not require re-embedding; switching the embedding provider does (see [Embedding rebuild workflow](#embedding-rebuild-workflow) below).

---

## Health surface

`GET /health` returns a JSON document with provider configuration so the frontend and operators can confirm the running posture without reading the environment:

| Field | Meaning |
|-------|---------|
| `llm_provider` | One of `groq`, `azure_openai`, `bedrock` (or unset if no LLM provider is configured) |
| `llm_configured` | Boolean — whether credentials for the selected LLM provider are present |
| `embedding_provider` | One of `openai`, `azure_openai`, `bedrock`, `none` |
| `embedding_configured` | Boolean — whether credentials for the selected embedding provider are present |
| `embedding_model` | Resolved model or deployment used for embeddings, or `null` when none is configured |
| `embedding_dim` | Vector dimension expected by the backend and pgvector column |

When any capability field is missing or `false`, the dependent UI surface degrades visibly (chat 503, meeting-prep placeholder, generate-note disabled) rather than silently failing. `/health` does not count populated embedding rows; chat surfaces that separately when retrieval is attempted.

---

## Groq (default demo)

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_CHAT_MODEL=llama-3.3-70b-versatile     # optional override
```

Groq is the recommended LLM provider for local synthetic demos and development. It is fast, inexpensive, and produces narrative quality sufficient for the pre-meeting summary, structured note generation, and chat completion routes. It does **not** provide embeddings; pair Groq with OpenAI (or Azure OpenAI / Bedrock) for embeddings.

---

## Azure OpenAI

Azure OpenAI is the natural fit for institutions with an existing Azure tenancy and a BAA-eligible Azure deployment. It is configured per-deployment-name, not per-model:

```bash
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=<deployment-name-for-chat-model>
AZURE_OPENAI_JSON_DEPLOYMENT=<deployment-name-for-json-capable-model>  # optional; falls back to chat deployment

# Embeddings (independent of LLM choice)
EMBEDDING_PROVIDER=azure_openai
AZURE_EMBEDDING_DEPLOYMENT=<deployment-name-for-embedding-model>
```

### Legacy aliases

Earlier configurations used `AZURE_OPENAI_DEPLOYMENT` (treated as the chat deployment) and `AZURE_OPENAI_MINI_DEPLOYMENT` (treated as the JSON-capable deployment). These names are still accepted as aliases for backward compatibility; prefer `AZURE_OPENAI_CHAT_DEPLOYMENT` and `AZURE_OPENAI_JSON_DEPLOYMENT` for new configurations.

---

## Amazon Bedrock

Bedrock is the natural fit for AWS-native deployments. Credentials follow the standard AWS resolution chain (environment variables, instance/role credentials, or a named profile).

```bash
LLM_PROVIDER=bedrock
AWS_REGION=us-west-2
AWS_BEDROCK_CHAT_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0
AWS_BEDROCK_JSON_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0  # optional; falls back to chat model
BEDROCK_PROFILE_NAME=<aws-profile>              # optional; use named profile from ~/.aws/credentials

# Embeddings (independent of LLM choice)
EMBEDDING_PROVIDER=bedrock
AWS_BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
```

### JSON-mode note

Not all Bedrock models support strict JSON-mode output the way OpenAI / Azure OpenAI do. The structured note generation route (`POST /notes/generate`) issues a JSON-shaped prompt and parses the response defensively: if the selected Bedrock model does not return valid JSON the route surfaces an explicit error rather than synthesizing a malformed note. Pick a Bedrock model with reliable JSON adherence (e.g. recent Claude family) for note-generation use; chat and meeting-prep paths are tolerant of unstructured text.

---

## Embedding rebuild workflow

Switching the embedding provider requires re-embedding **all** stored note vectors. Provider vector spaces are not interchangeable; mixing them silently corrupts retrieval. The supported workflow:

1. **Update `EMBEDDING_PROVIDER`** (and any provider-specific credentials and model/deployment fields) in `backend/.env`.
2. **Confirm health.** `curl http://127.0.0.1:8000/health` should report the new `embedding_provider` and `embedding_configured=true`.
3. **Clear existing embeddings.** There is no dedicated loader flag today; manually run `UPDATE notes SET embedding = NULL` against the target database so `scribe-load-corpus --embed` does not skip already-embedded rows.
4. **Re-embed.** Run `scribe-load-corpus --embed` against the same corpus JSONL artifact. Loader logs report rows processed and any retries.
5. **Verify.** `GET /health` should still report the expected `embedding_provider`, `embedding_model`, and `embedding_dim`; a chat request should now return grounded answers instead of the no-embeddings 503.

Re-embedding is idempotent and safe to retry; the loader uses transactional batches.

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| `GET /health` shows `llm_configured=false` despite credentials set | `LLM_PROVIDER` set to a value without all required env vars for that provider | Cross-check the provider section above; restart the API after `.env` edits |
| Chat returns 503 with "No embeddings in the database" | `notes.embedding` is empty for the current provider | Run `scribe-load-corpus --embed` |
| Chat returns 503 with "Embedding provider mismatch" or retrieval is empty after a provider switch | Stored embeddings were generated by a different provider | Follow the [Embedding rebuild workflow](#embedding-rebuild-workflow) (clear + re-embed) |
| Note generation returns "invalid JSON from model" on Bedrock | Selected Bedrock model does not reliably honor JSON-mode prompts | Switch `AWS_BEDROCK_CHAT_MODEL_ID` / `AWS_BEDROCK_JSON_MODEL_ID` to a model with strong JSON adherence (recent Claude family) |
| Azure OpenAI returns 404 on the deployment | `_CHAT_DEPLOYMENT` / `_EMBEDDING_DEPLOYMENT` is a model name, not the Azure deployment name | Use the deployment name from the Azure portal, not the underlying model id |
| Bedrock returns `UnauthorizedOperation` | Credentials chain not resolving the intended account/role | Set `BEDROCK_PROFILE_NAME` to a named profile in `~/.aws/credentials`, assume `AWS_BEDROCK_ROLE_ARN`, or export `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` |
| Pre-meeting summary returns a placeholder | LLM provider not configured for the selected `LLM_PROVIDER` | Either set credentials or leave the placeholder visible — the UI surfaces this state intentionally |
