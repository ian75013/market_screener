"""
Market Screener — Finnhub Fallback for Fundamentals

Finnhub API (gratuit tier: 60 req/min, no auth required for free public data).
Fallback quand yfinance est rate-limited.
"""
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

FINNHUB_API_BASE = "https://finnhub.io/api/v1"
FINNHUB_API_KEY = "cokxzzzqad6rg12n48p0"  # Free tier key (public)


def _safe_float(value) -> Optional[float]:
    """Safe float conversion."""
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_finnhub_fundamentals(ticker: str) -> dict[str, Optional[float]]:
    """
    Fetch fundamentals from Finnhub API.
    Free tier: 60 requests/minute (no auth required).
    
    Returns dict with fundamental fields, or empty dict on error.
    """
    try:
        # Finnhub Company Profile endpoint (includes basic fundamentals)
        resp = requests.get(
            f"{FINNHUB_API_BASE}/stock/profile2",
            params={"symbol": ticker, "token": FINNHUB_API_KEY},
            timeout=5,
        )
        if resp.status_code == 429:
            logger.warning(f"❌ Finnhub rate-limited for {ticker}")
            return {}
        
        if resp.status_code != 200:
            logger.debug(f"Finnhub profile failed for {ticker}: {resp.status_code}")
            return {}

        profile = resp.json()
        if not profile:
            return {}

        market_cap_millions = _safe_float(profile.get("marketCapitalization"))
        market_cap_billions = (market_cap_millions / 1000) if market_cap_millions and market_cap_millions > 0 else None
        
        return {
            "market_cap": market_cap_billions,
            "per": None,
            "peg": None,
            "pbr": None,
            "ps_ratio": None,
            "ev_ebitda": None,
            "ev_sales": None,
            "dividend_yield": None,
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
        }
    except requests.Timeout:
        logger.debug(f"Finnhub timeout for {ticker}")
        return {}
    except Exception as e:
        logger.debug(f"Finnhub error for {ticker}: {e}")
        return {}


async def enrich_fundamentals_finnhub(
    db,
    limit: int = 120,
    only_missing: bool = True,
) -> dict:
    """
    Fallback enrichment using Finnhub free tier.
    Less comprehensive than yfinance, but useful as a backup.
    """
    from sqlalchemy import or_, select
    from app.models import Stock

    query = select(Stock).order_by(Stock.id)

    if only_missing:
        query = query.where(
            or_(
                Stock.market_cap <= 0,
            )
        )

    result = await db.execute(query.limit(limit))
    rows = result.scalars().all()

    if not rows:
        return {
            "updated": False,
            "reason": "no_candidates",
            "checked": 0,
            "enriched": 0,
            "provider": "finnhub",
        }

    enriched_count = 0
    for stock in rows:
        snap = fetch_finnhub_fundamentals(stock.ticker)
        if not snap:
            continue

        if snap.get("market_cap") and snap["market_cap"] > 0:
            if stock.market_cap is None or (stock.market_cap or 0) <= 0:
                stock.market_cap = round(snap["market_cap"], 4)
                enriched_count += 1

    await db.commit()

    return {
        "updated": enriched_count > 0,
        "checked": len(rows),
        "enriched": enriched_count,
        "provider": "finnhub",
    }


def fetch_finnhub_quote(ticker: str) -> Optional[dict]:
    """
    Fetch current stock quote from Finnhub.
    Returns dict with price and basic data, or None on error.
    """
    try:
        resp = requests.get(
            f"{FINNHUB_API_BASE}/quote",
            params={"symbol": ticker, "token": FINNHUB_API_KEY},
            timeout=5,
        )
        if resp.status_code == 429:
            logger.info(f"❌ Finnhub rate-limited for {ticker}")
            return None
        
        if resp.status_code != 200:
            logger.warning(f"⚠️ Finnhub quote HTTP {resp.status_code} for {ticker}")
            return None

        data = resp.json()
        if not data or "c" not in data:
            logger.debug(f"Finnhub no price data for {ticker}")
            return None

        return data
    except requests.Timeout:
        logger.warning(f"⚠️ Finnhub timeout for {ticker}")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Finnhub quote error for {ticker}: {e}")
        return None


async def fetch_all_stocks_from_finnhub(min_valid: int | None = None) -> list[dict]:
    """
    Fetch all stocks from Finnhub as fallback when Yahoo Finance is rate-limited.
    Uses current quote endpoint (fast, no subscription needed).
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from app.yahoo_finance import STOCK_UNIVERSE
    
    logger.info("📡 Fetching data from Finnhub as Yahoo fallback for %s tickers", len(STOCK_UNIVERSE))
    
    stocks: list[dict] = []
    failed = 0
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_event_loop()
    
    for name, ticker_sym, country, sector, index, currency, isin in STOCK_UNIVERSE:
        try:
            # Clean ticker: remove country suffixes (.PA, .DE, .L, etc.)
            # Yahoo uses "TTE.PA" but Finnhub wants "TTE"
            if "." in ticker_sym:
                clean_ticker = ticker_sym.split(".")[0]
            else:
                clean_ticker = ticker_sym
            
            quote = await loop.run_in_executor(executor, fetch_finnhub_quote, clean_ticker)
            
            if quote is None or quote.get("c") is None or quote["c"] <= 0:
                failed += 1
                logger.debug(f"⚠️ Finnhub no quote for {ticker_sym} (cleaned: {clean_ticker})")
                continue
            
            price = float(quote["c"])
            prev_close = float(quote.get("pc", price))
            high_today = float(quote.get("h", price))
            low_today = float(quote.get("l", price))
            
            change_1d = 0.0
            if prev_close and prev_close > 0:
                change_1d = round((price - prev_close) / prev_close * 100, 2)
            
            stocks.append({
                "name": name,
                "ticker": ticker_sym,
                "country": country,
                "sector": sector,
                "market_index": index,
                "currency": currency,
                "isin": isin,
                "price": round(price, 4),
                "change_1d": change_1d,
                "change_1w": 0.0,
                "change_1m": 0.0,
                "change_3m": 0.0,
                "change_6m": 0.0,
                "change_ytd": 0.0,
                "change_1y": 0.0,
                "high_52w": high_today,
                "low_52w": low_today,
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
                "dist_mm50": None,
                "dist_mm200": None,
                "beta": None,
                "volatility": None,
                "volume_avg": None,
                "analyst_rating": None,
                "analyst_count": None,
                "target_price": None,
                "upside": None,
                "esg_score": None,
                "esg_env": None,
                "esg_social": None,
                "esg_gov": None,
                "ai_score_overall": 50.0,
                "ai_score_fundamental": 50.0,
                "ai_score_technical": 50.0,
                "ai_score_momentum": 50.0,
                "ai_score_risk": 50.0,
                "ai_signal": "NEUTRE",
            })
            
            if min_valid and len(stocks) >= min_valid:
                logger.info("✅ Early stop: collected %s tickers from Finnhub", len(stocks))
                break
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch {ticker_sym} from Finnhub: {e}")
            failed += 1
            continue
    
    if not stocks:
        logger.warning(
            "⚠️ Finnhub fallback collected 0 valid stocks (attempted %s, all failed)",
            len(STOCK_UNIVERSE),
        )
    
    logger.info(
        "✅ Fetched %s stocks from Finnhub (%s failed, fallback provider)",
        len(stocks),
        failed,
    )
    return stocks
