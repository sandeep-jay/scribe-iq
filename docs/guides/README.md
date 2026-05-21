# Developer guides

Entry point for **running and changing** this repository. Long-form specs live under [`docs/reference/`](../reference/); architecture inventory lives under [`docs/architecture/`](../architecture/). Product framing and diagrams: [`docs/overview/`](../overview/).

## Run each pillar

| Area | Guide |
|------|--------|
| **Quick start (end-to-end)** | [`QUICKSTART.md`](./QUICKSTART.md) |
| **LLM and embedding providers** | [`LLM_AND_EMBEDDING_PROVIDERS.md`](./LLM_AND_EMBEDDING_PROVIDERS.md) |
| Backend (FastAPI) | [`../../backend/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/backend/README.md) |
| Frontend (Next.js) | [`../../frontend/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/frontend/README.md) |
| Offline corpus builder | [`../../data_prep/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/data_prep/README.md) |
| AGBonnet HF clinical notes (historical precursors; do not extend) | [`../../corpus_pipelines/agbonnet_hf_clinical_notes/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/corpus_pipelines/agbonnet_hf_clinical_notes/README.md) |

## Node version

Frontend development assumes the Node version in [`.nvmrc`](https://github.com/sandeep-jay/scribe-iq/blob/main/.nvmrc):

```bash
nvm use
```

## When to update documentation

| Change | Update (same PR when practical) |
|--------|----------------------------------|
| API routes, env flags, DB schema, or as-built behavior | [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md) |
| High-level "what runs now" story | [`docs/architecture/CURRENT.md`](../architecture/CURRENT.md) |
| Product framing, scope, or deferred intent | [`docs/overview/PRODUCT_CONTEXT.md`](../overview/PRODUCT_CONTEXT.md) |
| Architecture diagrams, flags matrix, extension seams | [`docs/overview/SYSTEM_OVERVIEW.md`](../overview/SYSTEM_OVERVIEW.md) |
| Rationale, alternatives, or "what was non-obvious" | [`docs/overview/DESIGN_NOTES.md`](../overview/DESIGN_NOTES.md) |
| `data_prep/scripts/` contracts or pipeline behavior | [`docs/reference/corpus_offline_pipeline_v2_brief.md`](../reference/corpus_offline_pipeline_v2_brief.md) |
| Privacy / provider boundaries | [`docs/overview/`](../overview/) |
| Sequencing, scope, or product commitments | Relevant file under [`docs/roadmap/`](../roadmap/) |

## Local security checks

Set up local pre-commit hooks (including gitleaks) once per clone:

```bash
pip install pre-commit
pre-commit install
```

Run secret checks on demand:

```bash
pre-commit run gitleaks --all-files
```

### Tool attribution guards

This repo ships versioned git hooks under [`../../.githooks/`](https://github.com/sandeep-jay/scribe-iq/tree/main/.githooks/) that strip or block local tool attribution from commit messages and PR metadata.

- `commit-msg` and `prepare-commit-msg` remove known tool co-author trailers, "made with" footers, generated-by lines, and similar variants from the in-progress commit message.
- `pre-push` refuses to push commits whose messages still include disallowed attribution after the strip pass.

Wire them up once per clone:

```bash
./scripts/install_dev_hooks.sh
```

That sets `git config core.hooksPath .githooks` and makes the hook files executable. Do not bypass with `--no-verify`.

Authoring guidance: do not include local editor or AI-tool branding in commit messages, PR titles/bodies, review comments, or issue comments.


## Full documentation map

See [`docs/README.md`](https://github.com/sandeep-jay/scribe-iq/blob/main/docs/README.md).
