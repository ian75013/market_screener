# Troubleshooting Guide

## Fundamentals Still N/A

### Symptom
Screener displays N/A for PER, PBR, ROE columns even after hours.

### Diagnosis

1. **Check daemon is running:**
   ```bash
   docker compose logs backend | grep 'Scheduling fundamentals'
   ```
   Should show: `📘 Scheduling fundamentals daemon...`

2. **Check database has data:**
   ```bash
   docker compose exec -T postgres psql -U screener_user -d market_screener \
     -c "SELECT COUNT(*) as total, COUNT(per) as with_per FROM stocks;"
   ```
   If `with_per` = 0, enrichment hasn't run.

3. **Check for rate-limits:**
   ```bash
   docker compose logs backend | grep -i 'rate\|finnhub\|yfinance'
   ```
   Look for: `YFRateLimitError` or `rate limited`

### Solutions

**If daemon not running:**
```bash
docker compose restart backend
```

**If rate-limited (Yahoo):**
- Wait 1-4 hours for throttling window to clear
- Then run manual enrichment:
  ```bash
  curl -X POST 'http://localhost:8000/api/v1/admin/fundamentals/enrich?limit=10'
  ```

**If Finnhub rate-limited:**
- Reduce concurrency:
  ```env
  FUNDAMENTALS_BOOTSTRAP_ROUNDS=6  # Instead of 12
  ```
  Restart: `docker compose restart backend`

**If enrichment never completes:**
- This is normal! Maintenance runs forever every 30 minutes.
- Check recent activity:
  ```bash
  docker compose logs backend --tail 200 | grep 'Fundamentals maintenance'
  ```

---

## Backend Crashes on Startup

### Symptom
```
market-screener-backend  | ❌ Startup failed: ...
```

### Common Causes

1. **Postgres not ready:**
   ```bash
   docker compose ps
   # Check postgres is "Healthy"
   ```
   Solution: Wait 30 seconds and retry

2. **Postgres password mismatch:**
   ```bash
   docker compose down -v  # Reset volume
   docker compose up -d --build
   ```

3. **Python import error:**
   ```bash
   docker compose logs backend | tail -50
   ```
   Look for: `ModuleNotFoundError`, `ImportError`
   
   Solution: Check `requirements.txt` has all dependencies

4. **Config error:**
   ```bash
   docker compose exec -T backend python -c \
     "from app.config import settings; print(settings)"
   ```
   If fails, check `.env` syntax

---

## High Memory Usage

### Symptom
Backend container using >1GB RAM during fundamentals bootstrap.

### Cause
High concurrency (12 concurrent requests) × yfinance memory overhead.

### Solutions

1. **Reduce bootstrap concurrency:**
   ```env
   FUNDAMENTALS_BOOTSTRAP_ROUNDS=6  # Instead of 12
   FUNDAMENTALS_ROUND_LIMIT=60       # Instead of 120
   ```

2. **Increase pauses:**
   ```env
   FUNDAMENTALS_BOOTSTRAP_INTERVAL_SECONDS=180.0  # 3 min instead of 90s
   ```

3. **Restart with limits:**
   ```bash
   docker compose restart backend
   ```

---

## Airflow DAGs Not Running

### Symptom
Scheduled DAGs don't execute at expected times.

### Diagnosis

1. **Check Airflow is healthy:**
   ```bash
   docker compose ps airflow-scheduler
   # Should be "Up"
   ```

2. **Check DAGs are recognized:**
   ```bash
   docker compose exec airflow-scheduler \
     airflow dags list | grep market_screener
   ```

3. **Check pause status:**
   Visit http://localhost:8080
   - DAG should not be "paused" (toggle button)

4. **Check recent runs:**
   ```bash
   docker compose exec airflow-scheduler \
     airflow dags list-runs --dag-id market_screener_intraday_pipeline
   ```

### Solutions

**If DAGs don't appear:**
```bash
docker compose restart airflow-scheduler
```

**If paused:**
- Click web UI toggle or run:
  ```bash
  docker compose exec airflow-scheduler \
    airflow dags unpause market_screener_intraday_pipeline
  ```

**If dag definition error:**
```bash
docker compose logs airflow-scheduler | grep -i error
```
Check syntax in `airflow/dags/*.py`

---

## Database Full / Disk Space

### Symptom
```
ERROR:  could not extend file "base/1663/1688": No space left on device
```

### Solution

1. **Check disk usage:**
   ```bash
   docker exec market-screener-postgres \
     du -sh /var/lib/postgresql/data
   ```

2. **Cleanup old logs:**
   ```bash
   docker compose exec airflow-scheduler \
     airflow db clean --skip-archive  # Delete old task logs
   ```

3. **Reset database (destructive):**
   ```bash
   docker compose down -v  # WARNING: deletes all data
   docker compose up -d --build
   ```

---

## API Returns 500 Error

### Diagnosis

```bash
curl -v 'http://localhost:8000/api/v1/screen'
# Look at response body for error details
```

### Common Causes

1. **Database connection lost:**
   ```bash
   docker compose restart postgres backend
   ```

2. **Invalid filter syntax:**
   ```bash
   curl -X POST 'http://localhost:8000/api/v1/screen' \
     -H 'Content-Type: application/json' \
     -d '{"filters": {"per": {"min": "invalid"}}}'
   # Should fail with 400 Bad Request
   ```

3. **Bug in route handler:**
   ```bash
   docker compose logs backend --tail 100 | grep -i error
   ```
   Look for traceback

---

## Slow API Responses

### Symptom
`GET /api/v1/screen` takes >5 seconds.

### Causes

1. **Large dataset (40 stocks):** Expected ~1-2 sec
2. **Database not indexed:** Check query explain
3. **Fundamentals daemon hogging resources:** Check concurrency settings

### Solutions

1. **Add database indexes:**
   ```bash
   docker compose exec -T postgres psql -U screener_user -d market_screener \
     -c "CREATE INDEX idx_stocks_per ON stocks(per);"
   ```

2. **Reduce fundamentals concurrency:**
   ```env
   FUNDAMENTALS_BOOTSTRAP_ROUNDS=4
   FUNDAMENTALS_ROUND_LIMIT=60
   ```

---

## Quick Start Recovery

### "Nuclear" Reset (if everything broken)
```bash
# Stop everything
docker compose down -v

# Clean images
docker system prune -a

# Rebuild
docker compose up -d --build

# Watch startup
docker compose logs -f backend
```

Wait 10-15 minutes for full startup and fundamentals bootstrap.

---

## Getting Help

1. **Check logs:**
   ```bash
   docker compose logs -f backend  # Most useful
   docker compose logs -f postgres
   docker compose logs -f airflow-scheduler
   ```

2. **Review relevant docs:**
   - [FUNDAMENTALS_ENRICHMENT.md](FUNDAMENTALS_ENRICHMENT.md) — Data population
   - [SCHEDULED_REFRESH.md](SCHEDULED_REFRESH.md) — Airflow DAGs
   - [API_ENDPOINTS.md](API_ENDPOINTS.md) — API usage

3. **Contact:**
   - Open issue with:
     - Full error message (from logs)
     - Steps to reproduce
     - Environment (OS, Docker version, .env values)

---

**Version:** 1.0  
**Last Updated:** April 11, 2026
