# ROADMAP

## Overview
This document tracks the recent transformation of the Market Screener backend from simulated seed-only behavior to a Yahoo Finance-first ingestion pipeline with defensive handling for upstream rate limits.

Date of this update: 2026-04-08.

## Completed Changes

### 1. Dependency and Data-Source Foundation
Status: Completed

- Added Yahoo market-data dependency to backend requirements.
- Confirmed backend container build installs Yahoo-related stack correctly.

Files impacted:
- backend/requirements.txt

Outcome:
- The backend can now fetch open market data from Yahoo Finance.

### 2. Yahoo Fetcher Service Integration
Status: Completed

- Implemented and expanded Yahoo fetch logic in backend/app/yahoo_finance.py.
- Kept a curated stock universe with cross-market tickers.
- Added transformations from raw Yahoo response into internal Stock model-compatible fields.

Files impacted:
- backend/app/yahoo_finance.py

Outcome:
- The application can construct real stock payloads from Yahoo data instead of synthetic numbers.

### 3. Database Refresh Engine and False-Stats Wipeout
Status: Completed

- Implemented refresh_stocks_from_yahoo in backend/app/seed.py.
- Added false-stat detection rules (invalid/non-positive pricing).
- Added optional wipe behavior when false stats are detected in persisted rows.
- Added full replacement refresh flow when Yahoo data quality threshold is reached.

Files impacted:
- backend/app/seed.py

Outcome:
- Bad rows can be purged and replaced by fresh Yahoo-derived rows.

### 4. Startup Lifecycle Migration to Real Data First
Status: Completed

- Updated FastAPI startup lifecycle to run Yahoo refresh logic on boot.
- Added minimum-valid-row guard to avoid replacing data with low-quality/empty fetches.
- Preserved service readiness by allowing graceful skip behavior when Yahoo is unavailable.

Files impacted:
- backend/app/main.py

Outcome:
- Startup now prioritizes real data ingestion while preserving operational stability.

### 5. Operational Admin Endpoint
Status: Completed

- Added manual refresh endpoint for operators:
  - POST /api/v1/admin/refresh-yahoo
- Exposes min_required and wipe_if_false_stats controls via query parameters.

Files impacted:
- backend/app/routes.py

Outcome:
- Operators can trigger refreshes without restarting containers.

### 6. Rate-Limit Resilience Hardening
Status: Completed

- Reworked Yahoo retrieval strategy to chunked batch requests.
- Added retry with exponential backoff.
- Added early-stop logic when enough valid rows are collected.
- Added fail-fast logic for repeated empty chunks to prevent long startup stalls under provider throttling.
- Reduced noisy yfinance logger output to keep logs actionable.

Files impacted:
- backend/app/yahoo_finance.py
- backend/app/seed.py (pass-through of minimum required threshold)

Outcome:
- System now degrades gracefully under Yahoo throttling and still starts reliably.

## Current Runtime State (Verified)

- Containers healthy: postgres, backend, frontend.
- Health endpoint responds successfully.
- Yahoo refresh now succeeds partially under pressure and can load a valid subset (for example 24 rows), instead of failing with 0 rows after long warning floods.

## Design Decisions

- Primary source remains Yahoo Finance.
- No Alpaca fallback implemented yet (deferred intentionally per requirement ordering).
- Replace-only-on-quality-threshold avoids destructive updates from empty/rate-limited responses.

## Risks and Constraints

- Yahoo can still throttle by IP/network conditions.
- Data completeness may vary between runs depending on provider limits.
- Some advanced fundamentals/analyst fields are not always available in batch mode.

## Next Recommended Milestones

### Milestone A: Scheduled Refresh Job
Priority: High

- Add periodic async refresh worker (for example every 30-60 minutes).
- Add jitter to avoid fixed synchronized fetch bursts.

### Milestone B: Data Provenance and Freshness Metadata
Priority: High

- Add source, source_status, and source_updated_at to stock rows or metadata table.
- Surface provenance in API responses.

### Milestone C: Controlled Secondary Provider (Alpaca)
Priority: Medium

- Add optional fallback provider path only if Yahoo valid rows < threshold.
- Keep Yahoo as strict first provider.

### Milestone D: Observability and Alerting
Priority: Medium

- Add metrics counters: fetch_attempts, fetch_success, fetch_partial, fetch_skipped, rate_limited.
- Add startup refresh duration metrics and warning thresholds.

### Milestone E: Security and Operations
Priority: Medium

- Add admin endpoint protection (token or internal network restriction).
- Add request-level audit for refresh operations.

## Validation Checklist

Completed validations:
- Backend build and startup with new ingestion path.
- Health endpoint responsiveness post-change.
- Manual refresh endpoint callable.
- Logs confirm reduced startup blocking and partial-yet-valid Yahoo ingestion.

Pending validations:
- Long-run reliability over multiple hours/days.
- Scheduled refresh behavior once implemented.
- Alpaca fallback behavior once implemented.
