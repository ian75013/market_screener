# Project Documentation - Market Screener

Date: 2026-04-11

## 1. Project Scope

Market Screener is a full-stack stock screening platform with:

- FastAPI backend for data ingestion, screening, and AI analysis endpoints
- PostgreSQL as primary data store
- React/Vite frontend for interactive screening UI
- Apache Airflow for scheduled refresh pipelines
- Docker Compose for local and VPS orchestration
- OVH deployment automation scripts with optional Apache + Certbot

Main objective: provide robust screening even when external market providers are degraded, while keeping startup and operations simple on modest machines (local and VPS).

## 2. Repository Structure

- backend/: API, data models, ingestion pipeline, business logic
- frontend/: React application
- airflow/dags/: scheduled jobs triggering backend pipeline
- deploy/: OVH compose override, reverse proxy assets, deployment helpers
- scripts/: deployment and synchronization automation
- README.md: quick start and operator-friendly entry points
- ARCHITECTURE.md: architecture narrative
- DEPLOYMENT_OVH_AIRFLOW_PIPELINE.md: deployment and operations recap

## 3. Backend Architecture

### 3.1 Core Modules

- backend/app/main.py
  - FastAPI app setup
  - startup lifecycle (DB init + refresh pipeline)
  - health endpoint
- backend/app/config.py
  - environment-driven settings
  - database URL resolution from POSTGRES_* when DATABASE_URL is empty
  - startup tuning variables
- backend/app/database.py
  - async SQLAlchemy engine/session
- backend/app/models.py
  - Stock and SavedScreen ORM models
- backend/app/schemas.py
  - request/response models
- backend/app/routes.py
  - screening, filters, stock details, AI analysis, admin pipeline endpoints
- backend/app/screener.py
  - dynamic filtering/sorting/pagination logic
- backend/app/pipeline_refresh.py
  - multi-pass provider refresh orchestration
- backend/app/yahoo_finance.py
  - Yahoo fetch adapter (chunking, retries, early stop)
- backend/app/alpaca_finance.py
  - optional Alpaca fallback provider
- backend/app/seed.py
  - seed helpers including identity-only fallback universe

### 3.2 Startup Behavior

At backend startup:

1. DB schema is initialized
2. multi-pass refresh is attempted
3. if valid provider rows are available, table is refreshed
4. if no valid provider rows are available, identity-only fallback rows are inserted
5. application still becomes ready

Important: identity-only fallback does not inject fake market metrics. It stores action identity (name/ticker/country/sector/index/currency/isin) and leaves market metrics effectively unavailable for display.

## 4. Data Pipeline and Resilience

### 4.1 Multi-Pass Pipeline

Implemented in backend/app/pipeline_refresh.py:

- Pass 1: universe selection
- Pass 2: provider fetch (Yahoo primary, Alpaca optional fallback)
- Pass 3: local enrichment for missing derived fields
- Pass 4: quality gate (valid row threshold)
- Pass 5: replace/upsert in DB when gate passes

### 4.2 Provider Degradation Handling

When Yahoo is rate-limited:

- bounded retries are used
- early-stop logic limits unnecessary work
- quality gate prevents replacing good data with invalid data
- startup fallback ensures service availability

### 4.3 Scheduled Execution (Airflow)

- airflow/dags/market_screener_intraday_pipeline.py
- airflow/dags/market_screener_nightly_pipeline.py

Both DAGs trigger backend admin pipeline endpoint and run with resilient parameters.

## 5. Frontend Behavior

Frontend file: frontend/src/App.jsx

- consumes API from VITE_API_URL
- supports TradingView-like filters and multiple views
- now renders unavailable metrics as N/A
- supports identity-only fallback rows without breaking UI

N/A rendering rules include price placeholders and nullable technical/fundamental fields.

## 6. Configuration Model

### 6.1 Database Configuration

Preferred model:

- keep DATABASE_URL empty
- provide POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT

Backend builds async DSN automatically from POSTGRES_*.

### 6.2 Startup Tuning Variables

Used by backend startup refresh (config.py + main.py):

- STARTUP_MIN_REQUIRED
- STARTUP_PROVIDER_RETRIES
- STARTUP_PROVIDER_RETRY_DELAY_SECONDS
- STARTUP_INCLUDE_ALPACA_FALLBACK
- STARTUP_ENABLE_TECHNICAL_FALLBACK

Goal: keep boot time acceptable on modest machines and degraded provider conditions.

### 6.3 Airflow Admin Variables

- AIRFLOW_ADMIN_USERNAME
- AIRFLOW_ADMIN_PASSWORD
- AIRFLOW_ADMIN_FIRSTNAME
- AIRFLOW_ADMIN_LASTNAME
- AIRFLOW_ADMIN_EMAIL

No hardcoded admin password is required.

## 7. Compose Topology

### 7.1 Local Compose (docker-compose.yml)

Services:

- postgres
- backend
- frontend
- airflow-init
- airflow-scheduler
- airflow-webserver

Healthchecks are enabled for core services.

### 7.2 OVH Production Override (deploy/docker-compose.ovh.yml)

- binds service ports to controlled interfaces/ports
- runs backend in production mode
- includes startup tuning for smaller VPS
- keeps Airflow bind host configurable (VPN use case)

## 8. Deployment Automation (OVH)

Main scripts:

- scripts/sync_to_vps.sh
  - sync repository and env to remote host
- scripts/deploy_market_screener_ovh.sh
  - build/deploy compose stack remotely
  - optional docker install/bootstrap
  - wait/health checks
  - minimal rollback support

Reference env files:

- deploy/scripts/env.ovh.example
- deploy/scripts/env.ovh

Optional edge setup:

- deploy/scripts/install_apache_site.sh
- deploy/reverse-proxy/apache/market-screener.prod.example.conf

## 9. Networking and Security

### 9.1 Airflow on VPN

Production pattern:

- AIRFLOW_BIND_HOST set to VPN/private address (example: 10.8.0.1)
- AIRFLOW_REQUIRE_VPN=true

This avoids exposing Airflow publicly.

### 9.2 Reverse Proxy and HTTPS

- Apache reverse proxy templates are provided
- Certbot auto-provisioning can be enabled by env flags

### 9.3 Secrets Hygiene

- .env.example does not contain real secrets
- credentials are expected in deployment env files or host secrets

## 10. API Surface (High Level)

- GET /health
- POST /api/v1/screen
- GET /api/v1/screen/quick
- GET /api/v1/filters
- GET /api/v1/stock/{ticker}
- GET/POST AI analysis endpoints
- POST /api/v1/admin/pipeline/run
- GET /api/v1/admin/pipeline/profiles

## 11. Operations Playbook

### 11.1 Local Startup

- cp .env.example .env
- docker compose up --build
- verify: docker compose ps
- verify API: /health and /docs

### 11.2 When Provider Is Rate-Limited

Expected behavior:

- backend may spend time in startup fetch loop
- if insufficient valid rows, identity-only fallback is loaded
- API remains healthy
- frontend displays N/A for missing metrics

### 11.3 Refresh Later

After provider recovery, trigger refresh via admin pipeline endpoint or Airflow schedule.

## 12. Latest Changes (This Session)

### 12.1 Reliability and Startup

- removed synthetic numeric fallback during startup
- added identity-only fallback dataset (no fake metrics)
- kept API ready even with provider outage

Files:

- backend/app/main.py
- backend/app/seed.py

### 12.2 Frontend N/A Behavior

- unavailable metrics now render as N/A
- score widgets handle missing values safely

File:

- frontend/src/App.jsx

### 12.3 Healthcheck Tuning

- backend healthcheck timing adjusted to reduce false concerns during startup

File:

- docker-compose.yml

### 12.4 Startup Performance Tuning (Local + Production)

- startup refresh parameters made configurable in backend settings
- local compose defaults tuned for lighter startup
- OVH production override tuned as well (lower minimum and retries)
- env templates updated accordingly

Files:

- backend/app/config.py
- backend/app/main.py
- docker-compose.yml
- deploy/docker-compose.ovh.yml
- .env.example
- deploy/scripts/env.ovh.example
- deploy/scripts/env.ovh

## 13. Recommended Defaults

For modest machines (local and VPS):

- STARTUP_MIN_REQUIRED between 5 and 8
- STARTUP_PROVIDER_RETRIES=1
- STARTUP_PROVIDER_RETRY_DELAY_SECONDS between 0.5 and 1.0

Keep Airflow private in production and expose only through VPN/private interfaces.

## 14. Known Constraints

- external market data quality/latency depends on provider availability
- some advanced metrics can remain unavailable and display N/A
- first startup after provider degradation can take longer due to fetch attempts

## 15. Future Improvements

- separate status endpoint for readiness phase details (startup progress)
- provider circuit breaker to shorten startup further under hard throttling
- optional async post-start refresh mode for ultra-fast API readiness
- authentication on admin endpoints if exposed beyond trusted network
