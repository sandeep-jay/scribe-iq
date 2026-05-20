# Developer guides

Entry point for **running and changing** this repository. Long-form specs live under [`docs/reference/`](../reference/); architecture inventory and spine live under [`docs/architecture/`](../architecture/).

## Run each pillar

| Area | Guide |
|------|--------|
| Backend (FastAPI) | [`../../backend/README.md`](../../backend/README.md) |
| Frontend (Next.js) | [`../../frontend/README.md`](../../frontend/README.md) |
| Offline corpus builder | [`../../data_prep/README.md`](../../data_prep/README.md) |
| AGBonnet HF clinical notes (precursor scripts) | [`../../corpus_pipelines/agbonnet_hf_clinical_notes/README.md`](../../corpus_pipelines/agbonnet_hf_clinical_notes/README.md) |


## Node version

Frontend development assumes the Node version in [`.nvmrc`](../../.nvmrc):

```bash
nvm use
```

## When to update documentation

| Change | Update (same PR when practical) |
|--------|----------------------------------|
| API routes, env flags, DB schema, or as-built behavior | [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md) |
| High-level “what runs now” story | [`docs/architecture/CURRENT.md`](../architecture/CURRENT.md) |
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


### Commit message hook (strip Cursor trailer)

This repo ships a versioned commit-msg hook at [`../../.githooks/commit-msg`](../../.githooks/commit-msg) that removes this exact trailer if present:

- `Co-authored-by: Cursor <cursoragent@cursor.com>`

Install it locally (per clone):

```bash
ln -sf ../../.githooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

## Full documentation map

See [`docs/README.md`](../README.md).
