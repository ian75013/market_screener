# Scheduled Refresh Pipeline (Airflow)

## Overview

The Market Screener uses Apache Airflow 2.10.5 to orchestrate regular data refreshes. Two distinct DAGs run on different cadences to balance data freshness with resource efficiency.

**Status:** ✅ Active — Intraday (30-min) and nightly DAGs scheduled and executing.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │   Apache Airflow Orchestration   │
                    └─────────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
          ┌─────────────────────┐   ┌──────────────────────┐
          │  Intraday Pipeline  │   │  Nightly Pipeline    │
          │  (every 30 min)     │   │  (once per day)      │
          │  6-22 UTC weekdays  │   │  ~02:00 UTC          │
          └──────────┬──────────┘   └──────────┬───────────┘
                     │                         │
                     ├─► fetch_all_stocks()    └─► fetch_all_stocks()
                     ├─► update_database()        ├─► update_database()
                     └─► log results              └─► consolidate data
                                                     └─► log summary
```

## Intraday Pipeline (`market_screener_intraday_pipeline.py`)

### Schedule
```
Frequency:  Every 30 minutes
Hours:      06:00 - 22:00 UTC (market hours + some buffer)
Days:       Monday - Friday (weekdays only)
Cron:       */30 6-22 * * mon-fri
```

### Configuration

```python
FETCH_MIN_VALID = 24          # Stop after 24 valid rows
RETRIES = 2                   # Max 2 retries per chunk
CHUNK_SIZE = 8                # 8 tickers per API batch
INCLUDE_ALPACA_FALLBACK = True
```

**Rationale:**
- Light parameters avoid aggressive load
- 24 valid rows threshold = 3 minutes per pass (acceptable overhead)
- Early-stop prevents wasting resources on empty chunks

### Parameters

All configurable via environment variables (prefixed `AIRFLOW_INTRADAY_`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `FETCH_MIN_VALID` | 24 | Stop after N valid rows |
| `RETRIES` | 2 | Max retries per chunk |
| `CHUNK_SIZE` | 8 | Tickers per batch |

### Data Refreshed

- **Price:** Current price, 1d/1w/1m/3m/6m/YTD/1y changes
- **Technicals:** High/low 52w, volume, RSI, MACD (if available)
- **Basics:** Currency, sector, market cap

### Edge Cases Handled

- **Rate-limited:** Early-stop after 3 empty chunks
- **No valid data:** Skip refresh, don't overwrite good data
- **Partial recovery:** If <24 valid rows but >0, still update (allows gradual restoration)

---

## Nightly Pipeline (`market_screener_nightly_pipeline.py`)

### Schedule
```
Frequency:  Once per day
Time:       02:00 UTC (off-market hours, low API contention)
Days:       Every day (even weekends, for consistency)
Cron:       0 2 * * *
```

### Configuration

```python
FETCH_MIN_VALID = 50          # Higher threshold for heavy pass
RETRIES = 4                   # More retries than intraday
CHUNK_SIZE = 8                # Same batch size, higher retry count
INCLUDE_ALPACA_FALLBACK = True
```

**Rationale:**
- Heavy parameters ensure data quality after market close
- 50 valid rows + 4 retries = more thorough coverage
- Off-market hours = low API contention, no user-facing latency

### Data Refreshed

Same as intraday, but with more thorough coverage due to higher retry count.

### Purpose

- **Data consolidation:** Recover any gaps from intraday passes
- **Quality check:** Validate prices and eliminate false data
- **Backup window:** If intraday passes fail, nightly provides fallback
- **Off-peak:** Runs when markets closed, minimal user impact

---

## Multi-Pass Architecture

### Problem Solved
A single API call to Yahoo Finance returns ~50% of requested tickers (rest are empty/rate-limited). One pass = insufficient coverage.

### Solution: Offset Rotation

Each Airflow pass starts at a different offset in the ticker list:

```
Pass 1 (Intraday 09:00):     Fetch tickers 0-7,   14-21,  28-35,  ...
Pass 2 (Intraday 09:30):     Fetch tickers 8-15,  22-29,  36-43,  ...
Pass 3 (Intraday 10:00):     Fetch tickers 16-23, 30-37,  44-51,  ...
...
Pass N (Nightly 02:00):      All tickers with retries=4
```

**Benefits:**
- Distributes load across multiple requests
- No single ticker list exhaustion
- Handles provider rate-limiting gracefully
- Gradual data population from restart

### Implementation

```python
ticker_offset = (dag_run.execution_date.minute // 30) % num_passes
result = await fetch_all_stocks(
    offset=ticker_offset,
    chunk_size=8,
    ...
)
```

---

## Configuration via Environment Variables

### Precedence (highest to lowest)
1. `AIRFLOW_INTRADAY_*` variables (override DAG defaults)
2. DAG hard-coded defaults
3. Backend config defaults

### Example: Adjust Intraday Concurrence

```bash
# In .env or deploy/scripts/env.ovh
AIRFLOW_INTRADAY_FETCH_MIN_VALID=40  # More aggressive
AIRFLOW_INTRADAY_RETRIES=3           # More retries
```

Then restart Airflow:
```bash
docker compose restart airflow-scheduler
```

---

## Monitoring & Debugging

### View DAG Status

**Airflow Web UI:** http://localhost:8080
- Graphs showing pass success/failure
- Timing of each run
- Logs for debugging

### Command Line

```bash
# List DAGs
docker compose exec airflow-scheduler \
  airflow dags list

# Get recent runs
docker compose exec airflow-scheduler \
  airflow dags list-runs --dag-id market_screener_intraday_pipeline

# View task logs
docker compose logs -f airflow-scheduler | grep market_screener
```

### Key Logs to Watch

```bash
# Successful pass
2026-04-11 09:00:00 - INFO - ✅ Fetched 24 stocks (PASS)

# Rate-limited
2026-04-11 09:00:30 - WARNING - ⚠️ Aborted after 3 empty chunks (RATE LIMITED)

# Partial success
2026-04-11 09:01:00 - INFO - ⏸️ Startup pass 1/2: 18 rows (still loading)
```

---

## Failure Handling

### What Happens If Intraday Pass Fails?

1. Log error and continue to next scheduled pass (30 min later)
2. Nightly pass (~02:00 UTC) will attempt heavy recovery
3. User-facing API still works (returns existing cached data)
4. No data loss (only gaps in specific periods)

### What If Nightly Fails?

1. Next intraday pass continues regular schedule
2. No user impact (refresh is non-blocking)
3. Manual refresh available: `POST /api/v1/admin/refresh-yahoo`

### Recovery Procedure

**Manual refresh (if needed):**
```bash
curl -X POST 'http://localhost:8000/api/v1/admin/refresh-yahoo' \
  -H 'Content-Type: application/json' \
  -d '{"min_required": 30}'
```

**Restart Airflow scheduler:**
```bash
docker compose restart airflow-scheduler
```

---

## Performance Characteristics

| Metric | Intraday | Nightly |
|--------|----------|---------|
| Duration | 2-4 min | 5-10 min |
| API Calls | ~11 batches | ~20 batches |
| Tickers Updated | ~24-35 | ~40-50 |
| Rate-Limit Risk | Medium | Low |
| User Impact | Minimal | None (off-peak) |
| Resource Usage | Light | Heavy |

---

## Tuning Guide

### For More Frequent Updates

Problem: Still seeing N/A values or stale data
Solution: Reduce intraday interval from 30 minutes to 15 minutes

```env
# In .env
# Change DAG schedule in Airflow UI: */15 6-22 * * mon-fri
AIRFLOW_INTRADAY_FETCH_MIN_VALID=20  # Lower threshold
AIRFLOW_INTRADAY_RETRIES=1           # Fewer retries (faster)
```

### For Reduced API Load

Problem: High API costs or rate-limiting
Solution: Increase intraday interval to 60+ minutes

```env
AIRFLOW_INTRADAY_FETCH_MIN_VALID=50  # Higher threshold
AIRFLOW_INTRADAY_RETRIES=4           # More retries (thor ough)
```

### For Specific Data Feeds

Problem: Only certain tickers need updates (e.g., CAC40)
Solution: Implement sector-specific DAGs (future enhancement)

---

## Future Enhancements

### Weighted Scheduling
- Tech stocks: High-volatility → enrich every 15 min
- Utilities: Stable → enrich every 2 hours
- Config: `SCHEDULER_PROFILE=sector_weighted`

### Market-Hours Aware
- Market open/close times vary by exchange
- Adjust DAG schedule based on timezone
- Reduce off-hours API calls

### Smart Rate-Limit Detection
- Monitor HTTP 429 rates
- Auto-adjust batch size and delays
- Alert ops if provider becomes unavailable

---

**Document Version:** 1.0  
**Last Updated:** April 11, 2026  
**Status:** Production Active
