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

        # Finnhub also provides financials via /stock/financials-reported
        # But for free tier, profile has basic metrics
        
        market_cap_millions = _safe_float(profile.get("marketCapitalization"))
        market_cap_billions = (market_cap_millions / 1000) if market_cap_millions and market_cap_millions > 0 else None
        
        return {
            "market_cap": market_cap_billions,
            "per": None,  # Finnhub free tier doesn't have PER in profile
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
    
    Note: Finnhub profile2 doesn't have detailed valuation metrics in free tier.
    This is mainly useful for market cap updates.
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

        # Only really useful for market_cap from Finnhub
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
    
    Finnhub /stock/quote endpoint is fast and suitable as fallback when
    yfinance is rate-limited.
    """
    try:
        resp = requests.get(
            f"{FINNHUB_API_BASE}/quote",
            params={"symbol": ticker, "token": FINNHUB_API_KEY},
            timeout=5,
        )
        if resp.status_code == 429:
            logger.debug(f"Finnhub rate-limited for {ticker}")
            return None
        
        if resp.status_code != 200:
            logger.debug(f"Finnhub quote failed for {ticker}: {resp.status_code}")
            return None

        data = resp.json()
        if not data or "c" not in data:  # 'c' is current/close price
            return None

        return data  # Keys: c (close), h (high), l (low), o (open), pc (prev close), t (timestamp)
    except requests.Timeout:
        logger.debug(f"Finnhub timeout for {ticker}")
        return None
    except Exception as e:
        logger.debug(f"Finnhub quote error for {ticker}: {e}")
        return None


async def fetch_all_stocks_from_finnhub(min_valid: int | None = None) -> list[dict]:
    """
    Fetch all stocks from Finnhub as a fallback when Yahoo Finance is rate-limited.
    Uses current quote endpoint (fast, doesn't require subscription).
    
    Limitations:
    - Only current price (no 1-year history like Yahoo)
    - Will compute changes from current vs previous close only
    - Limited technical indicators compared to Yahoo
    
    Args:
        min_valid: Stop after collecting this many valid stocks
        
    Returns:
        List of stock dicts in same format as fetch_all_stocks() from yahoo_finance.py
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    # Use same universe as Yahoo
    from app.yahoo_finance import STOCK_UNIVERSE
    
    logger.info("📡 Fetching data from Finnhub as Yahoo fallback for %s tickers", len(STOCK_UNIVERSE))
    
    stocks: list[dict] = []
    failed = 0
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_event_loop()
    
    for name, ticker_sym, country, sector, index, currency, isin in STOCK_UNIVERSE:
        try:
            # Fetch quote in executor to avoid blocking
            quote = await loop.run_in_executor(executor, fetch_finnhub_quote, ticker_sym)
            
            if quote is None or quote.get("c") is None or quote["c"] <= 0:
                failed += 1
                continue
            
            price = float(quote["c"])  # Current/close price
            prev_close = float(quote.get("pc", price))  # Previous close
            high_today = float(quote.get("h", price))
            low_today = float(quote.get("l", price))
            
            # Compute 1-day change only (that's all we have)
            change_1d = 0.0
            if prev_close and prev_close > 0:
                change_1d = round((price - prev_close) / prev_close * 100, 2)
            
            # Create stock payload matching yahoo_finance format
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
                "change_1w": 0.0,  # Not available from Finnhub quote
                "change_1m": 0.0,
                "change_3m": 0.0,
                "change_6m": 0.0,
                "change_ytd": 0.0,
                "change_1y": 0.0,
                "high_52w": high_today,  # Use today's high as proxy
                "low_52w": low_today,    # Use today's low as proxy
                "market_cap": 0.0,  # Can fetch separately if needed
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
                # Technical scores are derived from prices, which we have minimally
                "ai_score_overall": 50.0,  # Neutral default
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
    
    logger.info(
        "✅ Fetched %s stocks from Finnhub (%s failed, fallback provider)",
        len(stocks),
        failed,
    )
    return stocks
