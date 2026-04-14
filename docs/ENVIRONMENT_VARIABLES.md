# Environment Variables Reference

All configuration is managed via `.env` file (local) or equivalent on production.

## Database

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
  # Full DSN (overrides individual POSTGRES_* vars if set)

POSTGRES_DB=market_screener
POSTGRES_USER=screener_user
POSTGRES_PASSWORD=screener_password_dev
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

## Environment

```env
ENVIRONMENT=development
  # Options: development, staging, production
```

## Startup Refresh

```env
STARTUP_MIN_REQUIRED=8
  # Minimum valid rows needed to consider refresh successful

STARTUP_FETCH_MIN_VALID=40
  # Target: stop after N valid rows (early-stop optimization)

STARTUP_TOPUP_ROUNDS=4
  # Background top-up passes after API is ready

STARTUP_TOPUP_INTERVAL_SECONDS=90.0
  # Delay between top-up passes

STARTUP_PROVIDER_RETRIES=1
  # Retry count for failed chunks

STARTUP_PROVIDER_RETRY_DELAY_SECONDS=1.0
  # Delay between retries

STARTUP_INCLUDE_ALPACA_FALLBACK=True
  # Fallback to Alpaca Data API if Yahoo unavailable

STARTUP_ENABLE_TECHNICAL_FALLBACK=True
  # Fallback to technical indicators if fundamentals unavailable
```

## Fundamentals Enrichment

```env
FUNDAMENTALS_ENABLED=True
  # Enable/disable entire fundamentals daemon

FUNDAMENTALS_BOOTSTRAP_ROUNDS=12
  # Aggressive startup rounds (local: 12, OVH: 6)

FUNDAMENTALS_BOOTSTRAP_INITIAL_DELAY_SECONDS=300.0
  # Wait 5 min after startup before bootstrap begins

FUNDAMENTALS_BOOTSTRAP_INTERVAL_SECONDS=90.0
  # Pause between bootstrap rounds (local: 90s, OVH: 120s)

FUNDAMENTALS_MAINTENANCE_INTERVAL_SECONDS=1800.0
  # 30 minutes between maintenance passes

FUNDAMENTALS_ROUND_LIMIT=120
  # Max tickers enriched per pass

FUNDAMENTALS_ONLY_MISSING=True
  # Skip already-populated rows
```

## Airflow Intraday Pipeline

```env
AIRFLOW_INTRADAY_CRON=*/30 6-22 * * 1-5
  # Scheduler cadence (UTC)

AIRFLOW_INTRADAY_MIN_REQUIRED=8
  # Minimum rows expected after intraday run

AIRFLOW_INTRADAY_FETCH_MIN_VALID=24
  # Stop after N valid rows (light threshold)

AIRFLOW_INTRADAY_PROVIDER_RETRIES=2
  # Max retries per chunk

AIRFLOW_INTRADAY_PROVIDER_RETRY_DELAY_SECONDS=2
  # Delay in seconds between retries
```

## Airflow Nightly Pipeline

```env
AIRFLOW_NIGHTLY_CRON=15 2 * * 1-5
  # Scheduler cadence (UTC)

AIRFLOW_NIGHTLY_MIN_REQUIRED=20
  # Minimum rows expected after nightly run

AIRFLOW_NIGHTLY_FETCH_MIN_VALID=50
  # Stop after N valid rows (heavy threshold)

AIRFLOW_NIGHTLY_PROVIDER_RETRIES=4
  # Max retries per chunk (more aggressive than intraday)

AIRFLOW_NIGHTLY_PROVIDER_RETRY_DELAY_SECONDS=3
  # Delay in seconds between retries
```

## Optional Provider Keys

```env
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_DATA_BASE_URL=https://data.alpaca.markets
  # Optional Alpaca fallback (not yet used)
```

## Server Configuration

```env
APP_NAME=Market Screener API
APP_VERSION=1.0.0
FRONTEND_URL=http://localhost:3000
```

---

## How to Apply Changes

### Local Development
1. Edit `.env`
2. Restart backend: `docker compose restart backend`

### Docker Compose Override
1. Edit `.env`
2. Rebuild & restart: `docker compose up -d --build`

### OVH VPS
1. Edit `deploy/scripts/env.ovh`
2. Source into deployment script
3. Restart containers: `docker compose -f deploy/docker-compose.ovh.yml restart`

### Kubernetes (Future)
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: market-screener-config
data:
  ENVIRONMENT: production
  FUNDAMENTALS_BOOTSTRAP_ROUNDS: "6"
  ...
```

---

**Version:** 1.0  
**Last Updated:** April 11, 2026
