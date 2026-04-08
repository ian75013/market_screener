"""
Market Screener — Alpaca Data Fetcher
Fallback open market data provider when Yahoo is rate-limited.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.config import settings
from app.yahoo_finance import STOCK_UNIVERSE

logger = logging.getLogger(__name__)


def _pct_change(closes: list[float], days: int) -> float:
    if len(closes) <= days:
        return 0.0
    start = closes[-days - 1]
    end = closes[-1]
    if start <= 0:
        return 0.0
    return round((end - start) / start * 100, 2)


def _build_payload_from_bars(meta: tuple[str, str, str, str, str, str, str], bars: list[dict]) -> dict | None:
    name, ticker, country, sector, market_index, currency, isin = meta
    if not bars:
        return None

    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    volumes: list[float] = []

    for bar in bars:
        try:
            closes.append(float(bar["c"]))
            highs.append(float(bar["h"]))
            lows.append(float(bar["l"]))
            volumes.append(float(bar["v"]))
        except (KeyError, TypeError, ValueError):
            continue

    if not closes:
        return None

    price = closes[-1]
    if price <= 0:
        return None

    ytd = 0.0
    current_year = datetime.now(UTC).year
    first_ytd_price: float | None = None
    for bar in bars:
        timestamp = bar.get("t")
        if not isinstance(timestamp, str):
            continue
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.year == current_year:
            try:
                first_ytd_price = float(bar["c"])
            except (KeyError, TypeError, ValueError):
                first_ytd_price = None
            break
    if first_ytd_price and first_ytd_price > 0:
        ytd = round((price - first_ytd_price) / first_ytd_price * 100, 2)

    dist_mm50 = None
    dist_mm200 = None
    if len(closes) >= 50:
        mm50 = sum(closes[-50:]) / 50
        if mm50 > 0:
            dist_mm50 = round((price - mm50) / mm50 * 100, 2)
    if len(closes) >= 200:
        mm200 = sum(closes[-200:]) / 200
        if mm200 > 0:
            dist_mm200 = round((price - mm200) / mm200 * 100, 2)

    daily_returns: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        curr = closes[i]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    volatility = None
    if daily_returns:
        mean = sum(daily_returns) / len(daily_returns)
        var = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
        volatility = round((var ** 0.5) * (252 ** 0.5) * 100, 2)

    momentum_score = max(0.0, min(100.0, 50 + _pct_change(closes, 252) * 1.2))
    technical_score = max(0.0, min(100.0, 50 + (dist_mm50 or 0) * 1.0))
    risk_score = max(0.0, min(100.0, 70 - (volatility or 25) * 0.8))
    fundamental_score = 50.0
    ai_overall = round(
        0.35 * fundamental_score
        + 0.25 * technical_score
        + 0.25 * momentum_score
        + 0.15 * risk_score,
        1,
    )
    ai_signal = (
        "ACHAT FORT" if ai_overall >= 70 else
        "ACHAT" if ai_overall >= 55 else
        "NEUTRE" if ai_overall >= 45 else
        "VENTE" if ai_overall >= 30 else
        "VENTE FORTE"
    )

    return {
        "name": name,
        "ticker": ticker,
        "country": country,
        "sector": sector,
        "market_index": market_index,
        "currency": currency,
        "isin": isin,
        "price": round(price, 4),
        "change_1d": _pct_change(closes, 1),
        "change_1w": _pct_change(closes, 5),
        "change_1m": _pct_change(closes, 21),
        "change_3m": _pct_change(closes, 63),
        "change_6m": _pct_change(closes, 126),
        "change_ytd": ytd,
        "change_1y": _pct_change(closes, 252),
        "high_52w": round(max(highs), 2) if highs else None,
        "low_52w": round(min(lows), 2) if lows else None,
        "market_cap": 0.0,
        "enterprise_value": None,
        "per": None,
        "peg": None,
        "pbr": None,
        "ps_ratio": None,
        "ev_ebitda": None,
        "ev_sales": None,
        "dividend_yield": 0.0,
        "payout_ratio": None,
        "roe": None,
        "roa": None,
        "roic": None,
        "margin_ebit": None,
        "margin_net": None,
        "margin_gross": None,
        "revenue_growth": None,
        "eps_growth": None,
        "ebitda_growth": None,
        "net_debt_ebitda": None,
        "current_ratio": None,
        "quick_ratio": None,
        "debt_equity": None,
        "fcf_yield": None,
        "interest_coverage": None,
        "rsi": None,
        "dist_mm50": dist_mm50,
        "dist_mm200": dist_mm200,
        "beta": None,
        "volatility": volatility,
        "volume_avg": round(sum(volumes[-20:]) / min(20, len(volumes)) / 1e6, 2) if volumes else None,
        "analyst_rating": None,
        "analyst_count": None,
        "target_price": None,
        "upside": None,
        "esg_score": None,
        "esg_env": None,
        "esg_social": None,
        "esg_gov": None,
        "ai_score_overall": ai_overall,
        "ai_score_fundamental": fundamental_score,
        "ai_score_technical": round(technical_score, 1),
        "ai_score_momentum": round(momentum_score, 1),
        "ai_score_risk": round(risk_score, 1),
        "ai_signal": ai_signal,
    }


async def fetch_all_stocks_from_alpaca(min_valid: int | None = None) -> list[dict]:
    """Fetch bars from Alpaca data API for US equities in the stock universe."""
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        logger.info("ℹ️ Alpaca credentials not configured; skipping Alpaca fallback")
        return []

    us_universe = [meta for meta in STOCK_UNIVERSE if meta[2] == "USA"]
    if not us_universe:
        return []

    symbols = [meta[1].replace("-", ".") for meta in us_universe]
    symbol_to_meta = {meta[1].replace("-", "."): meta for meta in us_universe}

    end = datetime.now(UTC)
    start = end - timedelta(days=380)

    headers = {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }

    results: list[dict] = []
    logger.info("📡 Fetching Alpaca fallback data for %s US symbols", len(symbols))

    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(0, len(symbols), 10):
            chunk = symbols[i:i + 10]
            params = {
                "symbols": ",".join(chunk),
                "timeframe": "1Day",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "limit": 500,
                "feed": "iex",
                "adjustment": "raw",
            }
            try:
                resp = await client.get(
                    f"{settings.alpaca_data_base_url.rstrip('/')}/v2/stocks/bars",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                bars_by_symbol = resp.json().get("bars", {})
            except Exception as exc:
                logger.warning("⚠️ Alpaca request failed for chunk %s: %s", chunk, exc)
                continue

            for symbol in chunk:
                bars = bars_by_symbol.get(symbol, [])
                meta = symbol_to_meta.get(symbol)
                if not meta:
                    continue
                payload = _build_payload_from_bars(meta, bars)
                if payload:
                    results.append(payload)

            if min_valid is not None and len(results) >= min_valid:
                logger.info("✅ Early stop on Alpaca fallback with %s valid rows", len(results))
                break

    logger.info("✅ Alpaca fallback returned %s valid stocks", len(results))
    return results
