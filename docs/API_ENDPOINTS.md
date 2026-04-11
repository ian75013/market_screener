# API Endpoints Reference

## Base URL
```
Local:  http://localhost:8000
Prod:   https://screener.example.com  (adjust for your domain)
```

## Authentication
Current implementation uses **no authentication**. All endpoints are public.

**Future:** Token-based auth planned for production.

---

## Screening Endpoints

### POST /api/v1/screen
**Get filtered/sorted stocks based on criteria**

```bash
curl -X POST 'http://localhost:8000/api/v1/screen' \
  -H 'Content-Type: application/json' \
  -d '{"limit": 10, "offset": 0}'
```

**Request Body:**
```json
{
  "limit": 10,
  "offset": 0,
  "filters": {},
  "sort": []
}
```

**Response:**
```json
{
  "stocks": [
    {
      "id": 2,
      "ticker": "MC.PA",
      "name": "LVMH",
      "price": 850.0,
      "per": 22.119,
      "pbr": 3.5556,
      "roe": 16.236,
      "marketCap": 239.6527,
      ...
    }
  ],
  "total": 40
}
```

**Query Parameters:**
- `limit` (int): Max results to return (default: 50)
- `offset` (int): Skip first N results (default: 0)

---

### GET /api/v1/ai/analyze/{ticker}
**Get AI analysis for specific stock**

```bash
curl 'http://localhost:8000/api/v1/ai/analyze/MC.PA'
```

**Response:**
```json
{
  "ticker": "MC.PA",
  "score": 75.5,
  "signals": {
    "global": "BUY",
    "fundamental": "STRONG",
    "technical": "HOLD",
    "momentum": "POSITIVE"
  },
  "analysis": "LVMH shows strong fundamentals..."
}
```

---

## Admin Endpoints

### POST /api/v1/admin/refresh-yahoo
**Manually trigger market data refresh**

```bash
curl -X POST 'http://localhost:8000/api/v1/admin/refresh-yahoo' \
  -H 'Content-Type: application/json' \
  -d '{"min_required": 30}'
```

**Query Parameters:**
- `min_required` (int, default: 8): Minimum valid rows before stopping
- `wipe_if_false_stats` (bool, default: false): Delete bad rows before refresh

**Response:**
```json
{
  "updated": true,
  "fetched": 28,
  "valid": 25
}
```

---

### POST /api/v1/admin/fundamentals/enrich
**Manually trigger fundamentals enrichment**

```bash
curl -X POST 'http://localhost:8000/api/v1/admin/fundamentals/enrich?limit=85&aggressive=true'
```

**Query Parameters:**
- `limit` (int, default: 120): Max tickers to enrich
- `aggressive` (bool, default: false): Use higher concurrency
- `only_missing` (bool, default: true): Skip already-populated rows

**Response:**
```json
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

---

## System Endpoints

### GET /health
**Health check (liveness probe)**

```bash
curl 'http://localhost:8000/health'
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-11T12:00:00Z"
}
```

---

### GET /docs
**OpenAPI/Swagger documentation**

Browser: http://localhost:8000/docs

Interactive API explorer with try-it-out functionality.

---

## Filter Examples

### Filter by PER (P/E Ratio)
```json
{
  "filters": {
    "per": {"min": 10, "max": 30}
  }
}
```

### Filter by ROE (Return on Equity)
```json
{
  "filters": {
    "roe": {"min": 15}
  }
}
```

### Filter by Market Cap
```json
{
  "filters": {
    "marketCap": {"min": 100}
  }
}
```

### Combine Filters
```json
{
  "filters": {
    "per": {"min": 10, "max": 25},
    "roe": {"min": 12},
    "marketCap": {"min": 50}
  },
  "sort": ["roe"]
}
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Not found |
| 500 | Internal server error |

---

**Version:** 1.0  
**Last Updated:** April 11, 2026
