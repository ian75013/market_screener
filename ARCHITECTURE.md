# ARCHITECTURE

## Purpose
This document describes the current technical architecture after migrating from synthetic seed data to a Yahoo Finance-first ingestion model with resilient startup behavior.

Date of this update: 2026-04-08.

## System Topology

The application runs as a 3-service Docker Compose stack:

- postgres: primary relational storage for normalized stock rows.
- backend: FastAPI service (business logic, ingestion, screening, API).
- frontend: React/Vite UI consuming backend endpoints.

Data flow summary:

1. Backend startup initializes database schema.
2. Backend attempts Yahoo refresh via ingestion pipeline.
3. If valid threshold is met, stock table is replaced with Yahoo-derived rows.
4. If threshold is not met, existing data is retained.
5. Frontend queries screening/stat APIs from backend.

## Backend Architecture

### A. Startup Lifecycle Layer (backend/app/main.py)

Responsibilities:

- Initialize DB connections and tables.
- Trigger refresh_stocks_from_yahoo during app startup.
- Enforce minimum valid-row threshold before replacement acceptance.
- Keep service operational even when Yahoo is temporarily rate-limited.

Why this matters:

- Startup is deterministic and data-aware.
- The service does not crash on provider throttling.
- Existing good data is preserved when refresh quality is insufficient.

### B. Ingestion Orchestration Layer (backend/app/seed.py)

Key function:

- refresh_stocks_from_yahoo(db, min_required, wipe_if_false_stats)

Responsibilities:

- Evaluate current DB for false stats.
- Optionally wipe clearly invalid rows.
- Fetch fresh Yahoo payloads.
- Validate payload quality before replacement.
- Execute full table replacement only when quality threshold is met.

Core safeguards:

- False-stat detection avoids persisting broken data.
- Threshold-based acceptance avoids replacing usable data with sparse/empty pulls.

### C. Provider Adapter Layer (backend/app/yahoo_finance.py)

Responsibilities:

- Define stock universe and ticker metadata.
- Retrieve Yahoo historical market data.
- Transform external payload into internal schema-compatible dictionary.
- Compute derived indicators from market series (performance windows, volatility, moving-average distance, basic AI-like scoring).

Rate-limit resilience strategy:

- Chunked batch downloads (small ticker groups).
- Retry loop with exponential backoff.
- Early stop when enough valid rows are already collected.
- Early abort under repeated fully empty chunks (global throttling signal).
- Reduced noisy external logger output for clearer operational logs.

Result:

- Faster startup convergence.
- Fewer warning floods.
- Better probability of partial successful ingestion under rate limiting.

### D. API Layer (backend/app/routes.py)

Operational endpoint added:

- POST /api/v1/admin/refresh-yahoo

Parameters:

- min_required: minimum valid Yahoo rows required for replacement.
- wipe_if_false_stats: whether to clear invalid rows prior to refresh logic.

Purpose:

- Enables on-demand refresh without app restart.
- Supports operational experimentation with threshold tuning.

## Data Model and Mapping

Storage model:

- The Stock ORM model remains the canonical persistence object.
- Yahoo payloads are transformed to Stock-compatible fields before insert.

Mapping notes:

- Price/performance metrics are computed directly from Yahoo historical close series.
- Some advanced fundamentals/analyst/ESG fields can be null when unavailable.
- AI score fields are currently derived heuristically from available market behavior where fundamental coverage is incomplete.

## Reliability Semantics

### Refresh Accept/Reject Contract

Accepted update:

- valid_payload_count >= min_required

Rejected update:

- valid_payload_count < min_required

On rejection:

- Database content is preserved (unless false-stat wipe rule already applied).
- Application startup proceeds with existing data to keep API available.

### False-Stats Handling

Current invalidity criterion includes:

- non-positive or missing price values (payload-side validation).

DB-side wipe mode can be toggled by caller to purge known-bad rows.

## Runtime Behavior Under Yahoo Rate Limiting

Observed previous behavior:

- Full-batch request often produced all-failed downloads.
- Startup stalled longer while warnings accumulated.

Current behavior after hardening:

- Chunked retries recover partial data more frequently.
- Startup terminates refresh early once threshold is met.
- Global no-data patterns abort early to reduce startup latency.
- Service becomes ready with best available validated dataset.

## Operational Guidance

### Recommended Startup Threshold

- Typical default: min_required = 20
- Lower value increases availability under heavy throttling but may reduce market breadth.
- Higher value improves coverage but may delay/skip updates more often.

### Manual Recovery

- Trigger POST /api/v1/admin/refresh-yahoo when provider limits cool down.
- Inspect backend logs for fetched/failed counts and unresolved chunk warnings.

### Health Verification

- /health for service readiness.
- /api/v1/stats for actual loaded stock count and distribution sanity.

## Security and Governance Notes

Current gap:

- Admin refresh endpoint is not yet protected by auth.

Recommendation:

- Add API key or internal-network restriction before production exposure.
- Add audit logging for each refresh trigger.

## Future Extension: Alpaca as Secondary Source

Architectural placement:

- Add provider adapter parallel to yahoo_finance.py.
- Keep provider policy in orchestration layer (seed.py):
  - Try Yahoo first.
  - If valid count below threshold, try Alpaca fallback.
  - Merge/reconcile while preserving source provenance.

Suggested enhancements before fallback:

- Source provenance fields.
- Provider-specific quality scoring.
- Conflict-resolution policy for overlapping tickers.

## File-Level Change Summary

Primary changed files in this migration phase:

- backend/app/main.py: startup refresh integration and guardrails.
- backend/app/seed.py: wipe/validate/replace orchestration.
- backend/app/yahoo_finance.py: provider adapter + resilience logic.
- backend/app/routes.py: operational refresh endpoint.
- backend/requirements.txt: Yahoo dependencies.

Documentation files created:

- ROADMAP.md
- ARCHITECTURE.md
