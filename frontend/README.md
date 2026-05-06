# Scribe IQ — Frontend

Next.js (App Router) UI for the clinical RAG demo: patients, chart, encounter, chat, and in-app docs.

## Documentation

- Architecture hub: [`docs/architecture/README.md`](../docs/architecture/README.md)
- Documentation map: [`docs/README.md`](../docs/README.md)
- UI roadmap: [`docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md`](../docs/roadmap/SCRIBE_IQ_UI_ROADMAP.md)

## Local development

From the repository root:

```bash
nvm use  # uses .nvmrc (Node 20)
cd frontend
npm install
npm run dev
```

Lint and E2E (parity with root README checklist): `npm run lint && npm run test:e2e`.

Open [http://localhost:3000](http://localhost:3000). Configure backend URL and feature flags using [`frontend/.env.example`](./.env.example); authoritative flag inventory lives in [`docs/architecture/IMPLEMENTED_BASELINE.md`](../docs/architecture/IMPLEMENTED_BASELINE.md).

## Framework reference

This app uses [Next.js](https://nextjs.org/docs).
