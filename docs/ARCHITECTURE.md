# Architecture Overview

## System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    Market Screener Platform                       │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Frontend Layer                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐    ┌────────────────────────────────┐  │
│  │  Screener UI        │    │  Airflow WebUI                 │  │
│  │  (React/Vite)       │    │  (DAG Monitoring)              │  │
│  │  :3000              │    │  :8080                         │  │
│  └──────────┬──────────┘    └────────────────┬───────────────┘  │
│             │                                 │                   │
└─────────────┼─────────────────────────────────┼───────────────────┘
              │                                 │
┌─────────────┼─────────────────────────────────┼───────────────────┐
│             │         API Layer              │                   │
│         ┌───▼───────────────────────────────┐ │                   │
│         │  FastAPI Backend                  │ │                   │
│         │  :8000                            │ │                   │
│         │                                    │ │                   │
│         │  ┌──────────────────────────────┐ │ │                   │
│         │  │ Routes:                      │ │ │                   │
│         │  │  POST /api/v1/screen         │ │ │                   │
│         │  │  POST /admin/refresh-yahoo   │ │ │                   │
│         │  │  POST /admin/fundamentals    │ │ │                   │
│         │  │  GET /health                 │ │ │                   │
│         │  └──────────────────────────────┘ │ │                   │
│         │                                    │ │                   │
│         │  ┌──────────────────────────────┐ │ │                   │
│         │  │ Business Logic:              │ │ │                   │
│         │  │  · yahoo_finance.py          │ │ │                   │
│         │  │  · fundamentals_refresh.py   │ │ │                   │
│         │  │  · finnhub_fallback.py       │ │ │                   │
│         │  │  · pipeline_refresh.py       │ │ │                   │
│         │  └──────────────────────────────┘ │ │                   │
│         └──────────────┬─────────────────────┘ │                   │
│                        │                       │                   │
└────────────────────────┼───────────────────────┼───────────────────┘
                         │                       │
┌────────────────────────┼───────────────────────┼───────────────────┐
│                        │   Data Layer          │                   │
│  ┌─────────────────────▼─────────────────────┐ │                   │
│  │  PostgreSQL 16                            │ │                   │
│  │  :5432                                    │ │                   │
│  │                                            │ │                   │
│  │  ┌──────────────────────────────────────┐ │ │                   │
│  │  │ stocks table:                        │ │ │                   │
│  │  │  · ticker, name, sector              │ │ │                   │
│  │  │  · price, change%, volume            │ │ │                   │
│  │  │  · PER, PBR, ROE, dividend_yield     │ │ │                   │
│  │  │  · market_cap, debt_equity, margins  │ │ │                   │
│  │  │  · 40+ metrics total                 │ │ │                   │
│  │  └──────────────────────────────────────┘ │ │                   │
│  └──────────────────────────────────────────┘ │                   │
│                        │ (raw data pulled)    │                   │
└────────────────────────┼────────────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────────────┐
│                        │  Scheduling Layer (Airflow)               │
│  ┌─────────────────────▼──────────────────────────────────────────┐ │
│  │  Apache Airflow 2.10.5                                         │ │
│  │  LocalExecutor (can scale to KubernetesExecutor)               │ │
│  │                                                                 │ │
│  │  ┌─────────────────────┐    ┌──────────────────────────────┐ │ │
│  │  │ Intraday DAG        │    │ Nightly DAG                  │ │ │
│  │  │ every 30 min        │    │ once per day                 │ │ │
│  │  │ 6-22 UTC weekdays   │    │ 02:00 UTC                    │ │ │
│  │  │                     │    │                              │ │ │
│  │  │ fetch_all_stocks()  │    │ fetch_all_stocks()           │ │ │
│  │  │ min_valid=24        │    │ min_valid=50                 │ │ │
│  │  │ retries=2           │    │ retries=4                    │ │ │
│  │  └─────────────────────┘    └──────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────┬──────────────────────────────────────────────────────────┘
            │
┌───────────┼──────────────────────────────────────────────────────────┐
│           │  External APIs                                           │
│  ┌────────▼──────────┐  ┌────────────────────┐                       │
│  │  Yahoo Finance    │  │  Finnhub API       │                       │
│  │  (yfinance lib)   │  │  (free tier)       │                       │
│  │                   │  │                    │                       │
│  │  Primary:         │  │  Fallback:         │                       │
│  │  · Ticker.info    │  │  · Rate-limit safe │                       │
│  │  · Stock prices   │  │  · 60 req/min      │                       │
│  │  · Fundamentals   │  │  · Market cap      │                       │
│  │                   │  │                    │                       │
│  └───────────────────┘  └────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Startup Flow (t=0 → t=20 min)

```
1. Docker Compose Up
   ↓
2. Database Initialization (PostgreSQL ready)
   ↓
3. Multi-Pass Yahoo Refresh (5 retries, min_valid=8)
   │
   ├─→ Pass 1: Fetch ~30 tickers → 25 valid
   │
   ├─→ Pass 2: 20-25 tickers → 20 valid (offset rotation)
   │
   └─→ Result: 40-45 stocks in DB
   ↓
4. If <40 stocks valid: Load identity-only universe (edges case)
   ↓
5. Fundamentals Daemon Scheduled (300s initial delay)
   ↓
6. Background Top-Up Passes (4 passes, 90s apart)
   │
   ├─→ Top-up 1: Recover additional rows
   │
   └─→ Top-up 4: Consolidate to min_valid=40
   ↓
7. Fundamentals Bootstrap (t=5min onward)
   │
   ├─→ Round 1: Enrich 120 stocks with yfinance.Ticker().info
   ├─→ Round 2: (90s later) Continue enrichment
   ├─→ ...
   └─→ Round 12: Complete after ~18 minutes
   ↓
8. API Ready at t=20min, databases fully enriched
```

### Intraday Refresh Flow (repeats every 30 min)

```
Airflow Scheduler triggers:
   ↓
market_screener_intraday_pipeline task
   ↓
fetch_all_stocks(min_valid=24, retries=2)
   ├─→ Batch API calls to Yahoo Finance (8 tickers/batch)
   ├─→ Early-stop after 24 valid rows
   └─→ Skip if rate-limited after 3 empty chunks
   ↓
Update database (non-destructive, only add missing data)
   ↓
Log results (24-35 stocks updated per pass)
   ↓
Next pass in 30 minutes
```

### Fundamentals Enrichment Flow

```
source: yfinance.Ticker(ticker).info
   ├─→ Extract PER, PBR, ROE
   ├─→ Extract margins, growth rates
   └─→ Extract debt ratios, yields

If yfinance RateLimit Error:
   └─→ Fallback to Finnhub API
       └─→ Extract market_cap (safe, less rate-limited)

Store in PostgreSQL stocks table
   │
   ├─→ Non-destructive: only write if field is NULL
   ├─→ Batch commits (per chunk of 12 stocks)
   └─→ Continue on individual ticker failures
   ↓
Log enrichment metrics (enriched count, fields written)
```

## Component Responsibilities

### Frontend (React/Vite, port 3000)
- Display stock screening table
- Filter/sort UI controls
- AI analysis modal for individual stocks
- Real-time data fetching from backend API

### Backend API (FastAPI, port 8000)
**Responsibilities:**
- REST API for screening requests
- Business logic: filtering, sorting, scoring
- Database abstraction (ORM)
- Admin endpoints for manual refresh/enrichment
- Health checks and observability

**Key Modules:**
- `main.py` — FastAPI app, lifespan management
- `routes.py` — Endpoint definitions
- `models.py` — SQLAlchemy ORM (Stock entity)
- `config.py` — Settings from environment
- `database.py` — PostgreSQL connection pooling
- `yahoo_finance.py` — Yahoo data fetching
- `fundamentals_refresh.py` — Enrichment logic
- `finnhub_fallback.py` — Fallback provider
- `pipeline_refresh.py` — Multi-pass orchestration

### Data Layer (PostgreSQL, port 5432)
**Storage:**
- `stocks` table: 40 stocks with 60+ columns
  - Basic: ticker, name, sector
  - Market: price, changes, volume
  - Fundamentals: PER, PBR, ROE (20+ metrics)
  - Metadata: currency, index, ISIN

**Indexes:**
- Primary key on `id`
- Planned: `per`, `pbr`, `roe`, `market_cap` for fast filtering

### Scheduling Layer (Apache Airflow, port 8080)
**Responsibilities:**
- Define and schedule DAGs (directed acyclic graphs)
- Trigger Yahoo refresh on fixed intervals
- Log execution details and metrics
- Provide UI for monitoring

**DAGs:**
- `market_screener_intraday_pipeline.py`: Every 30 min
- `market_screener_nightly_pipeline.py`: Once per day

**Executor:** Local (can upgrade to Kubernetes future)

### External APIs
**Primary (yfinance):**
- Curated Python library wrapping Yahoo Finance
- Comprehensive: prices, technicals, fundamentals
- Rate-limited under load
- No authentication required

**Fallback (Finnhub):**
- REST API with free tier
- 60 requests/minute limit (sufficient for maintenance)
- Primary use: market cap when yfinance throttles

## Resilience Patterns

### Rate-Limit Handling

```
Scenario: Yahoo throttles during high load
   ↓
yfinance raises: YFRateLimitError
   ↓
fundamentals_refresh detects exception
   ↓
Sets: _rate_limit_hit = True
   ↓
Fallback to Finnhub for current batch
   ↓
Reduce concurrency slightly for next batch (0.5s pause instead of 0.15s)
   ↓
Continues iterating (no crash, no data loss)
```

### Multi-Pass Rotation

```
40 tickers in universe
   ↓
Airflow Pass 1 (09:00): Fetch offset 0-7     → 6 valid
Airflow Pass 2 (09:30): Fetch offset 8-15    → 5 valid
Airflow Pass 3 (10:00): Fetch offset 16-23   → 7 valid
Airflow Pass 4 (10:30): Fetch offset 24-31   → 4 valid
   ↓
Result: 22/40 stocks updated in 2 hours (distributed load)
```

### Graceful Degradation

| Component Down | System Status | User Experience |
|---|---|---|
| yfinance API | Degraded | Stale prices (6+ hours old) |
| Finnhub API | Degraded | ~22 stocks/day enriched (maintenance) |
| PostgreSQL | DOWN | API returns 500, UI unresponsive |
| Airflow scheduler | DOWN | No automatic refreshes (manual only) |
| Frontend | DOWN | API still works (curl accessible) |

## Scalability

### Current (10-100 stocks)
- Single backend instance
- PostgreSQL on single host
- Airflow LocalExecutor
- Sufficient for CAC40 + extended universe

### Medium (100-1000 stocks)
- 2-3 backend replicas (behind load balancer)
- PostgreSQL with read replicas
- Airflow KubernetesExecutor
- Increase fundamentals `ROUND_LIMIT` to 200-400

### Large (1000+ stocks)
- Horizontal backend scaling
- PostgreSQL cluster + sharding
- Airflow distributed schedulers
- Possibly split by sector/region DAGs

## Technologies

### Languages & Frameworks
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (async)
- **Frontend:** JavaScript/TypeScript + React + Vite
- **Scheduling:** Python + Apache Airflow 2.10.5
- **Database:** PostgreSQL 16 + asyncpg

### Libraries
- **Data fetching:** yfinance, requests
- **API:** FastAPI, Uvicorn, Pydantic
- **ORM:** SQLAlchemy + alembic (migrations)
- **Async:** asyncio + concurrent.futures
- **Frontend:** React, Axios, TailwindCSS

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **Orchestration:** Airflow (LocalExecutor)
- **Future:** Kubernetes (via Airflow KubernetesExecutor)

## Deployment Environments

### Local Development
- `docker-compose.yml` — Single file, all services
- `.env` — Environment-specific config
- Volumes: PostgreSQL persistent, Airflow logs
- Suitable for: Development, testing, demo

### OVH VPS
- `deploy/docker-compose.ovh.yml` — VPS-specific overrides
- `deploy/scripts/env.ovh` — VPS configuration
- Manual docker-compose CLI (no Docker Desktop)
- Suitable for: Staging, light production

### Kubernetes (Future)
- `deploy/k8s/base/` — Core manifests
- `deploy/k8s/overlays/{dev,staging,prod}/` — Environment overrides
- Kustomize for configuration management
- Suitable for: Production, high availability

---

**Document Version:** 2.0  
**Last Updated:** April 11, 2026  
**Status:** Production Architecture (with Finnhub Fallback Resilience)
