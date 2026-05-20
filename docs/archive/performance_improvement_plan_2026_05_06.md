# Performance improvement plan (2026-05-06)

> **Archived (2026-05).** Preserved for design lineage. Current authoritative source: [`docs/architecture/IMPLEMENTED_BASELINE.md`](../architecture/IMPLEMENTED_BASELINE.md). Map: [`docs/README.md`](../README.md).


## Scope

Target user-facing latency in these flows:

1. `GET /patients/{id}/meeting-prep?refresh=false` (cached path)
2. `GET /patients/{id}/meeting-prep?refresh=true` (regeneration path)
3. `GET /patients`, `GET /patients/stats` baseline reads
4. DB request queuing risk under concurrent slow external LLM calls

## Baseline observations

- Cache hit path still rebuilt a full meeting-prep context bundle before checking cache freshness.
- Cache hit path still ran safety/audit hashing and inserted an `ai_interactions` row synchronously.
- Meeting-prep context builder queried notes with patient/domain filters + sort by `session_date, created_at`, but lacked a composite index tailored to that access pattern.
- Asyncpg pool used implicit defaults only.

## Implemented changes

### 1) Cache-hit fast path (backend)

In `backend/app/api/patients.py`:

- move cache lookup earlier in endpoint flow
- validate freshness with lightweight `notes_fingerprint(...)` query
- return immediately on cache hit
- skip full context bundle construction and skip audit write on cache hit

### 2) DB index improvements (alembic)

Add migration `backend/alembic/versions/20260506_004_performance_indexes.py`:

- `ix_notes_patient_domain_session_created`
- partial index `ix_notes_patient_domain_longitudinal_recent` for `longitudinal_context IS NOT NULL`

### 3) Pool tuning knobs (backend config)

In `backend/app/config.py` and `backend/app/main.py`:

- `db_pool_min_size` (default `2`)
- `db_pool_max_size` (default `20`)
- `db_pool_command_timeout_s` (default `30`)

These settings are now wired into `asyncpg.create_pool(...)`.

## Latency measurements

Environment: local dev machine, FastAPI in reload mode, same DB/corpus, point-in-time comparisons.

### Before changes

- `patients/stats`: avg `2.8ms`
- `patients?limit=200`: avg `3.6ms`
- `meeting-prep cached`: avg `8.2ms`, p50 `7.0ms`
- `meeting-prep refresh=true`: `~2051.7ms` sample (LLM-dependent)

### After code + index changes

- `patients/stats`: avg `2.3ms`, p50 `1.7ms`
- `patients?limit=200`: avg `4.1ms`, p50 `4.1ms`
- `meeting-prep cached`: avg `3.6ms`, p50 `3.5ms`, p95 `4.6ms`
- `meeting-prep refresh=true`: highly variable, observed `~36.1s` sample (external LLM latency dominated)

## Interpretation

- Cached-path latency improved materially (roughly ~2x in local runs) by removing avoidable per-request work.
- Refresh path remains dominated by external LLM/network behavior, not DB/cache mechanics.
- Pool/index tuning reduces risk under load and improves query plan fit for meeting-prep reads.

## Follow-up opportunities

1. Avoid holding DB connection during external LLM call (split DB read/call/write phases).
2. Add pgvector ANN index migration for chat retrieval (`ivfflat`/`hnsw`) once corpus size warrants.
3. Add endpoint-level timing middleware or OpenTelemetry spans for p95/p99 visibility.
4. Optionally introduce stale-while-revalidate for meeting prep cache.



## Post-index re-sample (same machine/session)

Second run after migration + cache-path refactor:

- `patients/stats`: p50 `1.84ms`, p95 `2.92ms`, avg `2.06ms`
- `patients?limit=200`: p50 `3.63ms`, p95 `11.55ms`, avg `4.92ms`
- `meeting-prep cached`: p50 `3.33ms`, p95 `9.47ms`, avg `4.24ms`
- `meeting-prep refresh=true`: sample `3183ms` (`degraded=false`)

This confirms cached responses are now in low-single-digit milliseconds in local dev, while refresh-path remains dominated by external model latency variability.


## Phase-2 implementation (connection hold-time reduction + ANN index)

Implemented additional performance work:

1. **Split DB vs external-call phases** in `GET /patients/{id}/meeting-prep`:
   - acquire DB conn for cache/fingerprint and bundle reads
   - release conn before Groq call
   - reacquire conn for cache upsert + audit insert

2. **Split DB vs embedding/LLM phases** in `POST /chat`:
   - acquire/release for prechecks + optional patient longitudinal read
   - release conn during `embed_query_text(...)`
   - reacquire for retrieval query
   - release conn during Groq call
   - reacquire for audit insert

3. **pgvector ANN index migration**:
   - `20260506_005_notes_embedding_ivfflat.py`
   - creates `ix_notes_embedding_ivfflat_cosine` on `notes(embedding vector_cosine_ops)` with `lists=100`

### Phase-2 benchmark sample

- `patients/stats`: p50 `1.47ms`, p95 `2.61ms`, avg `1.74ms`
- `patients?limit=200`: p50 `2.67ms`, p95 `3.29ms`, avg `2.80ms`
- `meeting-prep cached`: p50 `2.83ms`, p95 `4.98ms`, avg `3.42ms`
- `meeting-prep refresh=true`: avg `25872ms` with high variance (`2391ms`, `30140ms`, `45084ms`)

Interpretation: server-side hot paths are now consistently fast; long-tail latency is dominated by external LLM provider variance.
