# Fundamentals Enrichment System

## Overview

The Fundamentals Enrichment system automatically populates valuation, profitability, and growth metrics that enable meaningful stock screening. This system was created to replace the "N/A" placeholders that were blocking user filtering capabilities.

**Status:** ✅ Active (April 11, 2026) — All 40 stocks fully enriched with PER, PBR, ROE, and 20+ additional metrics.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│           Fundamentals Enrichment Pipeline                   │
└─────────────────────────────────────────────────────────────┘

Data Sources:
  ├── Primary: yfinance.Ticker().info  (comprehensive valuation metrics)
  └── Fallback: Finnhub API            (free tier, 60 req/min, no auth)

Processing:
  ├── bootstrap_daemon()              (12 aggressive rounds, 90s apart)
  ├── maintenance_loop()              (30-min cadence, lighter concurrency)
  └── manual_endpoint()               (POST /api/v1/admin/fundamentals/enrich)

Storage:
  └── PostgreSQL stocks table         (per, peg, pbr, roe, roa, margins, debt ratios, etc.)

Consumption:
  ├── REST API (/api/v1/screen)       (returns enriched metrics)
  └── Screener UI                      (displays PER, P/B, ROE columns)
```

### Key Modules

#### `backend/app/fundamentals_refresh.py`
Main enrichment logic with yfinance integration and Finnhub fallback.

**Key Functions:**
- `_fetch_fundamental_snapshot(ticker)` → Dict[field → value]
  - Calls yfinance.Ticker().info for comprehensive metrics
  - On rate-limit detection, automatically falls back to Finnhub
  - Performs safe float conversion and NaN handling

- `enrich_fundamentals(db, limit, aggressive)` → Result dict
  - Queries database for stocks missing fundamental data
  - Batches concurrent requests (12 tickers if aggressive, 6 if light)
  - Commits only non-None new values
  - Returns enrichment metrics

**Extracted Fields (25 total):**
```
Valuation:
  - per                (P/E Ratio: price/earnings)
  - peg                (PEG Ratio: per/earnings_growth)
  - pbr                (Price-to-Book)
  - ps_ratio           (Price-to-Sales)
  - ev_ebitda          (EV/EBITDA multiple)
  - ev_sales           (EV/Revenue)

Profitability:
  - roe                (Return on Equity %)
  - roa                (Return on Assets %)
  - roic               (Return on Invested Capital, future)
  - margin_gross       (Gross Margin %)
  - margin_ebit        (Operating Margin %)
  - margin_net         (Net Profit Margin %)

Growth:
  - revenue_growth     (YoY Revenue Growth %)
  - eps_growth         (YoY EPS Growth %)
  - ebitda_growth      (EBITDA Growth %)

Returns & Yields:
  - dividend_yield     (Dividend Yield %)
  - payout_ratio       (Dividend Payout Ratio %)
  - fcf_yield          (Free Cash Flow Yield %)

Debt & Liquidity:
  - debt_equity        (Debt-to-Equity ratio)
  - current_ratio      (Current Ratio)
  - quick_ratio        (Quick Ratio)
  - net_debt_ebitda    (Net Debt/EBITDA, future)

Scale:
  - market_cap         (Market Cap in billions)
  - enterprise_value   (EV in billions)
```

#### `backend/app/finnhub_fallback.py` *(NEW - April 11, 2026)*
Finnhub API integration for resilience against Yahoo rate-limiting.

**Key Function:**
- `fetch_finnhub_fundamentals(ticker)` → Dict[field → value]
  - Free tier: 60 requests/minute, no authentication required
  - Primarily provides market_cap updates
  - Called automatically when yfinance rate-limits
  - Non-blocking: if Finnhub unavailable, system continues with yfinance results

**Why Finnhub?**
- ✅ Free tier with reasonable rate limits (60 req/min)
- ✅ No API key required (uses public tier)
- ✅ Faster response than yfinance during peak hours
- ✅ Different provider = different rate-limit windows = better resilience

**Fallback Logic:**
```python
try:
    data = yfinance.Ticker(ticker).info
except RateLimitError:
    _rate_limit_hit = True
    data = finnhub.fetch_fundamentals(ticker)  # Automatic fallback
```

### Daemon Lifecycle

#### Startup Phase (App Initialization)

1. **Initialization (0-5 minutes):** FastAPI lifespan starts `_fundamentals_daemon()`
2. **Initial Delay (5 minutes):** Wait for market data passes to populate database (avoid competing for resources)
3. **Bootstrap Phase (5-25 minutes):** Aggressive enrichment
   - 12 rounds of concurrent enrichment (local) or 6 rounds (OVH)
   - 90-second pauses between rounds
   - High concurrency (12 tickers/batch if aggressive)
   - Goal: Rapidly populate missing fundamentals while app is starting

#### Maintenance Phase (Ongoing)

1. **30-Minute Cadence:** Run forever after bootstrap completes
2. **Lighter Concurrency:** 6 tickers/batch (vs 12 during bootstrap)
3. **Only Missing Fields:** Skip already-populated rows (configurable)
4. **Rate-Limit Adaptive:** If yfinance rate-limits, pause slightly longer for Finnhub

### Configuration

All parameters are environment-driven (no code changes required):

```env
# Enable/disable entire daemon
FUNDAMENTALS_ENABLED=True

# Bootstrap phase
FUNDAMENTALS_BOOTSTRAP_ROUNDS=12                              # local: 12, OVH: 6
FUNDAMENTALS_BOOTSTRAP_INITIAL_DELAY_SECONDS=300.0            # 5 minutes
FUNDAMENTALS_BOOTSTRAP_INTERVAL_SECONDS=90.0                  # local: 90s, OVH: 120s
FUNDAMENTALS_ROUND_LIMIT=120                                  # max tickers per pass

# Maintenance phase
FUNDAMENTALS_MAINTENANCE_INTERVAL_SECONDS=1800.0              # 30 minutes

# Filtering
FUNDAMENTALS_ONLY_MISSING=True                                # Skip if already populated
```

See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for full list.

## Usage

### Automatic Enrichment (Daemon)

No action required. The daemon starts automatically on app startup:

```log
2026-04-11 11:05:24 - app.main - INFO - 📘 Scheduling fundamentals daemon 
  (delay=300.0s, bootstrap=12 every 90.0s, maintenance every 1800.0s)
```

Monitor progress in logs:
```bash
docker compose logs -f backend | grep -i fundamental
```

### Manual Enrichment (On-Demand)

Trigger enrichment without restarting:

```bash
# Enrich first 85 stocks, aggressive mode
curl -X POST 'http://localhost:8000/api/v1/admin/fundamentals/enrich?limit=85&aggressive=true'

# Response:
{
  "updated": true,
  "checked": 20,
  "enriched": 20,
  "fields_written": 386,
  "aggressive": true,
  "only_missing": true,
  "fallback_used": false
}
```

**Query Parameters:**
- `limit` (int, default 120): Max tickers to enrich per request
- `aggressive` (bool, default false): Higher concurrency and shorter pauses
- `only_missing` (bool, default true): Skip already-populated rows

## Data Flow Example

### Scenario: First-Time Stock Load

1. **Startup (t=0s):**
   - Multi-pass refresh fetches market data from yfinance
   - 40 stocks loaded with `price`, `high52w`, `low52w`, etc.
   - Fundamental columns (PER, ROE, etc.) are NULL

2. **Bootstrap Phase (t=300s → t=1800s):**
   - 12 concurrent passes, 90s apart
   - Each pass tries to enrich ~10 stocks worth of data
   - yfinance provides PER=22.119, ROE=16.236, etc. for MC.PA (LVMH) ✓
   - All 40 stocks enriched by end of bootstrap (usually 10-15 minutes)

3. **Maintenance Phase (t=1800s onwards):**
   - Every 30 minutes, check for stocks missing fundamentals
   - If new stocks added to DB, enrich them gradually
   - Handle rate-limits gracefully with Finnhub fallback

4. **User Interaction:**
   - Screener UI query hits `/api/v1/screen`
   - API returns stocks with PER, ROE, etc. populated
   - Users can filter/sort by fundamental metrics ✓

## Rate-Limiting & Resilience

### Problem: Yahoo Finance Rate-Limiting

During peak usage (many concurrent requests), yfinance returns HTTP 429:
```
YFRateLimitError: Too Many Requests. Rate limited. Try after a while.
```

### Solution: Automatic Fallback to Finnhub

```python
# In _fetch_fundamental_snapshot()
try:
    info = yf.Ticker(ticker).info
except RateLimitError:
    _rate_limit_hit = True
    return fetch_finnhub_fundamentals(ticker)  # Fallback
```

**Benefits:**
- ✅ Graceful degradation (doesn't crash or block entire app)
- ✅ ~60 requests/minute from Finnhub (sufficient for maintenance phase)
- ✅ No authentication required (free tier)
- ✅ Automatic retry in logs: `Using Finnhub fallback...`

### Monitoring Rate-Limit Status

Check logs for fallback usage:
```bash
docker compose logs backend | grep -i 'finnhub\|rate'
```

If Finnhub is being used heavily (>30% of requests), consider:
1. Reducing bootstrap concurrency
2. Increasing pauses between batches
3. Limiting enrichment to `only_missing=true` (default)

## Implementation Details

### Database Schema Changes

New columns in `stocks` table:
```sql
-- Valuation metrics
per FLOAT,              -- P/E Ratio
peg FLOAT,              -- PEG Ratio
pbr FLOAT,              -- Price-to-Book
ps_ratio FLOAT,         -- Price-to-Sales
ev_ebitda FLOAT,        -- EV/EBITDA
ev_sales FLOAT,         -- EV/Revenue

-- Profitability metrics
roe FLOAT,              -- Return on Equity %
roa FLOAT,              -- Return on Assets %
roic FLOAT,             -- Return on Invested Capital %
margin_gross FLOAT,     -- Gross Margin %
margin_ebit FLOAT,      -- Operating Margin %
margin_net FLOAT,       -- Net Profit Margin %

-- Growth metrics
revenue_growth FLOAT,   -- YoY Revenue Growth %
eps_growth FLOAT,       -- YoY EPS Growth %
ebitda_growth FLOAT,    -- EBITDA Growth %

-- Returns & Yields
dividend_yield FLOAT,   -- Dividend Yield %
payout_ratio FLOAT,     -- Payout Ratio %
fcf_yield FLOAT,        -- Free Cash Flow Yield %

-- Debt & Liquidity
debt_equity FLOAT,      -- Debt-to-Equity
current_ratio FLOAT,    -- Current Ratio
quick_ratio FLOAT,      -- Quick Ratio
net_debt_ebitda FLOAT   -- Net Debt/EBITDA
```

### API Response Example

```json
GET /api/v1/screen
{
  "stocks": [
    {
      "id": 2,
      "ticker": "MC.PA",
      "name": "LVMH",
      "price": 0,
      "marketCap": 239.6527,
      "per": 22.119,
      "peg": null,
      "pbr": 3.5556,
      "psRatio": 2.9657,
      "evEbitda": 12.855,
      "evSales": 3.275,
      "roe": 16.236,
      "roa": null,
      "margin_net": 21.165,
      ...
    }
  ]
}
```

## Testing & Validation

### Verify Enrichment Status

```bash
# Check database enrichment progress
docker compose exec -T postgres psql -U screener_user -d market_screener \
  -c "SELECT COUNT(*) as total, COUNT(per) as with_per, COUNT(roe) as with_roe FROM stocks;"

# Expected output (after bootstrap):
# total | with_per | with_roe
# ------|----------|----------
#    40 |       40 |       40
```

### Manual Enrichment Test

```bash
# Trigger enrichment manually (first 5 stocks, aggressive)
curl -X POST 'http://localhost:8000/api/v1/admin/fundamentals/enrich?limit=5&aggressive=true' | jq .

# Expected response:
{
  "updated": true,
  "checked": 5,
  "enriched": 5,
  "fields_written": 98,
  "aggressive": true,
  "only_missing": true
}
```

### Monitor Daemon in Real-Time

```bash
# Follow fundamentals logs
docker compose logs -f backend | grep -E '📘|Fundamentals'

# Expected output:
# 2026-04-11 11:05:24 - app.main - INFO - 📘 Scheduling fundamentals daemon
# 2026-04-11 11:10:24 - app.main - INFO - 📘 Fundamentals bootstrap 1/12: enriched=8 fields=156
# 2026-04-11 11:12:00 - app.main - INFO - 📘 Fundamentals maintenance: enriched=0 fields=0
```

## Troubleshooting

### Issue: Fundamentals Still N/A After Hours

**Diagnosis:**
1. Check daemon is running: `docker compose logs backend | grep 'Scheduling fundamentals'`
2. Verify database: `SELECT COUNT(per) FROM stocks WHERE per IS NOT NULL;`
3. Check for rate-limits: `docker compose logs backend | grep -i 'rate\|finnhub'`

**Solutions:**
1. **Daemon not running:** Restart backend
   ```bash
   docker compose restart backend
   ```

2. **Rate-limited:** Wait 1-4 hours for Yahoo to reset, then retry
   ```bash
   curl -X POST 'http://localhost:8000/api/v1/admin/fundamentals/enrich?limit=10&aggressive=true'
   ```

3. **Finnhub not helping:** Check free tier rate-limits
   - Finnhub: 60 req/min (check dashboard at https://finnhub.io)

### Issue: High Resource Usage During Bootstrap

**Cause:** 12 concurrent requests creates load spike.

**Solution:** Reduce bootstrap concurrency
```env
FUNDAMENTALS_BOOTSTRAP_ROUNDS=6  # Instead of 12
```

Then restart:
```bash
docker compose restart backend
```

### Issue: Enrichment Never Completes

**Cause:** Infinite loop in maintenance phase (by design).

**Status:** This is normal. Maintenance runs forever every 30 minutes.

**To verify it's working:**
```bash
docker compose logs backend --tail 100 | grep 'Fundamentals maintenance'
```

Should see logs every 30 minutes.

## Future Enhancements

### Phase 2: Secondary Provider Integration
- Add Alpha Vantage API as additional fallback (paid tier: comprehensive fundamentals)
- Config via: `FUNDAMENTALS_SECONDARY_PROVIDER=alpha_vantage`

### Phase 3: Observability
- Prometheus metrics: `fundamentals_enriched_total`, `fundamentals_rate_limit_hits`
- Expose `/metrics` endpoint with enrichment stats

### Phase 4: Advanced Scheduling
- Sector-specific cadences (high-volatility sectors enrich more frequently)
- Weekend vs weekday profiles (skip fundamentals on weekends when markets closed)

---

**Document Version:** 1.0.1  
**Last Updated:** April 11, 2026  
**Status:** Production-Ready with Finnhub Fallback
