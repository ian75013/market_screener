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
