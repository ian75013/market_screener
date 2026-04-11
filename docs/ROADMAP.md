# ROADMAP - Market Screener Active Development

## Overview
This document tracks the Market Screener platform evolution from simulated seed-only behavior through Yahoo Finance-first ingestion, rate-limit resilience, scheduled refresh pipelines, environment harmonization, database recovery, and dedicated fundamental data enrichment with Finnhub fallback.

**Latest Update:** April 11, 2026 — Finnhub fallback implemented for fundamentals enrichment. All 40 stocks fully enriched with PER, PBR, ROE, and 20+ metrics. System now resilient to Yahoo rate-limiting.

## Completed Milestones

### Phase 1: Foundation (2026-01-15 through 2026-03-31)

✅ **1.1** — Yahoo Finance Integration
- Implemented yfinance wrapper in `backend/app/yahoo_finance.py`
- Chunked batch requests with retry logic
- Transformed Yahoo responses to Stock model fields

✅ **1.2** — Database Refresh Engine
- Implemented `refresh_stocks_from_yahoo()` with validation
- False-stat detection (invalid prices, negative data)
- Rate-limit resilience (early-stop, exponential backoff)

✅ **1.3** — Startup Lifecycle
- FastAPI lifespan management with async initialization
- Multi-pass startup refresh with fallback to identity-only universe
- Background top-up passes for data recovery

✅ **1.4** — Admin Endpoints
- Added `POST /api/v1/admin/refresh-yahoo` for manual refresh
- Configurable parameters: `min_required`, `wipe_if_false_stats`

### Phase 2: Scheduling & Automation (2026-04-01 through 2026-04-08)

✅ **2.1** — Airflow Integration
- Implemented Apache Airflow 2.10.5 DAGs
- Intraday pipeline: Every 30 minutes (6-22 UTC, weekdays)
- Nightly pipeline: Once per day (~02:00 UTC)
- Light parameters (intraday): min_valid=24, retries=2
- Heavy parameters (nightly): min_valid=50, retries=4

✅ **2.2** — Configuration Harmonization
- All scheduling vars exposed via environment variables
- Synchronized across local dev, Docker Compose, OVH deployment
- Files updated: `.env`, `.env.example`, `deploy/scripts/env.ovh*`, `docker-compose.yml`

✅ **2.3** — Multi-Pass Rotation
- Added `ticker_offset` parameter to distribute load
- Each Airflow pass starts at different offset
- Prevents synchronized IP-level rate-limiting

✅ **2.4** — Database Recovery
- Procedure: `docker compose down -v && docker compose up -d --build`
- Resolves Postgres credential mismatches
- Complete volume reset validated

### Phase 3: Fundamentals Enrichment (2026-04-08 through 2026-04-11)

✅ **3.1** — Dedicated Fundamentals Module
- Created `backend/app/fundamentals_refresh.py` (180 lines)
- Extracts 25 fundamental metrics from yfinance.Ticker().info
- Fields: PER, PEG, PBR, ROE, ROA, margins, growth, debt ratios, yields, FCF

✅ **3.2** — Daemon Lifecycle Management
- Bootstrap phase: 12 aggressive rounds (90s apart), 5-min initial delay
- Maintenance phase: Every 30 minutes, lighter concurrency
- Graceful shutdown: Cancels tasks on app exit
- Configuration via environment variables (all tunable)

✅ **3.3** — Finnhub Fallback (April 11, 2026)
- Created `backend/app/finnhub_fallback.py`
- Free tier: 60 requests/minute, no authentication required
- Automatic fallback triggered on yfinance rate-limit (HTTP 429)
- Provides market_cap updates when yfinance throttles
- Prevents single-provider dependency

✅ **3.4** — Admin Endpoint
- `POST /api/v1/admin/fundamentals/enrich` added to `routes.py`
- Query params: `limit`, `aggressive`, `only_missing`
- Returns enrichment metrics: `{updated, checked, enriched, fields_written, fallback_used}`
- Manual trigger without server restart

✅ **3.5** — Full System Validation
- Startup: All components healthy (postgres, backend, frontend, airflow)
- Data population: 40 stocks loaded with market data
- Enrichment: 40/40 stocks (100%) enriched with fundamentals
- Rate-limit handling: Tested and fallback working
- API response: Fundamentals correctly returned in `/api/v1/screen`

## Current Status (April 11, 2026)

### Operational Systems

```
✅ Backend API              : Healthy (FastAPI + async)
✅ PostgreSQL 16           : Healthy (40 stocks in DB)
✅ Frontend Screener       : Loaded (React/Vite)
✅ Airflow Scheduler       : Active (intraday + nightly DAGs)
✅ Airflow Webserver       : Active (http://localhost:8080)
✅ Market Data             : 40 stocks with prices, technicals
✅ Fundamental Data        : 40 stocks with PER, ROE, etc.
✅ Fallback Provider       : Finnhub (60 req/min, free)
```

### Data Completeness

```
Total Stocks:                    40
With Market Data:                40  (100%)
With Fundamental Metrics:        40  (100%)
  - With PER:                    40  (100%)
  - With PBR:                    40  (100%)
  - With ROE:                    40  (100%)
  - With Market Cap:             40  (100%)
```

### Refresh Cadence

```
Startup:
  - Multi-pass Yahoo refresh (aggressive startup)
  - Fundamentals daemon bootstrap (12 rounds, 90s apart)

Intraday:
  - Airflow every 30 minutes (light parameters)
  - Covers prices, technicals, basic metrics

Nightly:
  - Airflow once per day (~02:00 UTC)
  - Heavy pass, consolidation window

Fundamentals:
  - Bootstrap: Complete within 20 minutes of startup
  - Maintenance: Every 30 minutes ongoing
  - Provider: yfinance → Finnhub fallback on rate-limit
```

## Known Limitations & Trade-offs

### Rate-Limiting
- **yfinance:** Free, comprehensive, but aggressive rate-limiting during peak hours
- **Finnhub:** Slower (60 req/min), limited metrics in free tier, but more reliable
- **Workaround:** Automatic fallback ensures degraded-but-functional service

### Data Coverage
- Some fundamentals (PEG, advanced metrics) not available on all tickers (especially international)
- Gaps are acceptable; filtering still works on available fields
- Partial data > No data ✓

### Deployment Targets
- ✅ Local dev (Docker Compose) — Fully tested
- ✅ OVH VPS (bash scripts) — Tested manually
- ⏳ Kubernetes — Planned, not yet validated at scale

## Pending Milestones

### Milestone 4: Secondary Provider (Medium Priority)
**Target:** May 2026

Add paid secondary provider option (Alpha Vantage, FMP) for sustained outages:
- Keep yfinance primary (free, comprehensive)
- Add optional secondary via config
- Fallback if primary rate-limited for >1 hour
- Reduce single-vendor dependency risk

**Implementation:**
- Create `backend/app/alpha_vantage_fallback.py`
- Add `FUNDAMENTALS_SECONDARY_PROVIDER=alpha_vantage` config
- Update `fundamentals_refresh.py` to try secondary on sustained rate-limit

**Expected Benefit:** Eliminate 24-hour stalls during Yahoo outages

### Milestone 5: Observability & Metrics (Medium Priority)
**Target:** May 2026

Add Prometheus metrics for fundamentals enrichment:
- `fundamentals_enriched_total` — Counter
- `fundamentals_fields_written_total` — Counter
- `fundamentals_rate_limit_hits_total` — Counter (by provider)
- `fundamentals_bootstrap_duration_seconds` — Histogram
- `fundamentals_maintenance_duration_seconds` — Histogram

**Implementation:**
- Add Prometheus client library to `requirements.txt`
- Instrument `fundamentals_refresh.py` with metrics
- Expose `/metrics` endpoint in `main.py`
- Integrate with Airflow metrics dashboard

**Expected Benefit:** Visibility into enrichment health, early warning of provider issues

### Milestone 6: Data Provenance (Low Priority)
**Target:** June 2026

Track which provider populated which fields:
- Add `fundamentals_source` (yfinance, finnhub, alpha_vantage) to stocks table
- Add `fundamentals_updated_at` timestamp
- Return provenance in API responses

**Benefits:**
- Audit trail for data quality
- Identify which provider works best by metric
- Understand data freshness for filtering/sorting

### Milestone 7: Advanced Scheduling (Low Priority)
**Target:** July 2026

Context-aware refresh profiles:
- Weekday vs weekend scheduling (skip weekends when markets closed)
- Market hours vs after-hours profiles
- Sector-specific cadences (high-volatility sectors enrich more frequently)
- Time-zone aware scheduling (market open/close times vary by exchange)

**Benefits:**
- Resource efficiency (no weekend refreshes)
- Better data freshness for volatile sectors
- Reduced API costs (fewer unnecessary calls)

## Files Changed in Phase 3 (April 2026)

### New Files Created
```
backend/app/fundamentals_refresh.py      (180 lines) — Main enrichment logic
backend/app/finnhub_fallback.py          (125 lines) — Finnhub integration
docs/FUNDAMENTALS_ENRICHMENT.md          (400 lines) — Detailed documentation
```

### Modified Files
```
backend/requirements.txt                 (+requests for HTTP calls to Finnhub)
backend/app/main.py                      (+_fundamentals_daemon lifespan hooks)
backend/app/config.py                    (+7 fundamentals config settings)
backend/app/routes.py                    (+POST /admin/fundamentals/enrich endpoint)
docker-compose.yml                       (+FUNDAMENTALS_* env vars to backend)
deploy/docker-compose.ovh.yml            (+FUNDAMENTALS_* env vars)
.env, .env.example                       (+fundamentals and airflow scheduling vars)
deploy/scripts/env.ovh*                  (+fundamentals and airflow scheduling vars)
ROADMAP.md                               (this file, moved to docs/)
README.md                                (updated with fundamentals reference)
```

### Documentation Structure (New)
```
docs/
  ├── INDEX.md                           (Navigation hub)
  ├── ROADMAP.md                         (this file)
  ├── FUNDAMENTALS_ENRICHMENT.md         (Deep dive on fundamentals system)
  ├── SCHEDULED_REFRESH.md               (Airflow DAGs documentation)
  ├── API_ENDPOINTS.md                   (REST API reference)
  ├── DEPLOYMENT.md                      (Local/OVH deployment guides)
  ├── ENVIRONMENT_VARIABLES.md           (Config reference)
  └── TROUBLESHOOTING.md                 (Diagnostics & solutions)
```

## Validation Checklist

### Implementation ✅
- [x] Fundamentals enrichment module created
- [x] Daemon lifecycle integrated (bootstrap + maintenance)
- [x] yfinance integration with safe type conversion
- [x] Finnhub fallback implemented
- [x] Manual admin endpoint created
- [x] Configuration externalized (no hardcoding)
- [x] Error handling and graceful degradation
- [x] Logging added (fallback detection, enrichment outcomes)

### Integration ✅
- [x] Backend builds without errors
- [x] Database schema supports fundamental fields
- [x] API returns fundamentals in `/api/v1/screen` responses
- [x] Docker Compose updated with FUNDAMENTALS_* env vars
- [x] OVH deployment updated
- [x] Startup flows tested end-to-end

### Testing ✅
- [x] Manual enrichment endpoint functional
- [x] 40 stocks successfully enriched (PER, PBR, ROE all populated)
- [x] yfinance → Finnhub fallback verified (tested rate-limit scenario)
- [x] Database verification (COUNT queries show 100% coverage)
- [x] API response validation (fundamentals returned correctly)
- [x] Daemon startup, bootstrap, and maintenance phases logged

### Production Readiness ✅
- [x] Rate-limit resilience (automatic fallback)
- [x] Graceful shutdown (task cancellation)
- [x] Configuration flexibility (all params env-driven)
- [x] Error recovery (non-blocking, continues on individual ticker failures)
- [x] Resource constraints respected (configurable concurrency, pauses)
- [x] Documentation complete (3000+ lines for Phase 3)

## Migration Notes

### For OVH Deployment
1. Pull latest code
2. Update `.env` with new FUNDAMENTALS_* and AIRFLOW_* variables
3. Rebuild backend: `docker build -t market-screener-backend:latest backend/`
4. Restart backend: `docker compose -f deploy/docker-compose.ovh.yml restart backend`
5. Monitor: `docker logs -f market-screener-backend | grep -i fundamental`

### For Local Development
1. Run: `docker compose down -v && docker compose up -d --build`
2. Daemon will start automatically; bootstrap completes in ~20 minutes
3. Check progress: `docker compose logs -f backend | grep 📘`
4. Verify data: `curl http://localhost:8000/docs` → Try `/api/v1/screen`

## Next Steps

1. **Monitor fundamentals enrichment** (ongoing)
   - Watch logs for rate-limit recovery times
   - Track Finnhub fallback usage
   - Adjust concurrency/delays if needed

2. **Validate screener UI** (short-term)
   - Confirm PER, P/B, ROE columns display values (not N/A)
   - Test filtering/sorting on fundamental metrics
   - Gather user feedback on data completeness

3. **Plan Phase 4 implementation** (medium-term)
   - Decide on secondary provider (Alpha Vantage vs FMP vs other)
   - Design metrics collection strategy
   - Schedule implementation sprint

---

**Document Version:** 2.0.0  
**Last Updated:** April 11, 2026  
**Status:** Production Active with Finnhub Fallback Resilience
