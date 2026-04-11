"""
Market Screener — Fundamental Enrichment

Dedicated enrichment pass for valuation/profitability/growth fields that are often
missing after fast market-data passes.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Stock
from app.finnhub_fallback import fetch_finnhub_fundamentals

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8)
_rate_limit_hit = False  # Track if yfinance rate-limit hit


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        # NaN check
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fetch_fundamental_snapshot(ticker: str) -> dict[str, float | None] | None:
    """Blocking Yahoo fundamentals fetch for one ticker, with Finnhub fallback on rate-limit."""
    global _rate_limit_hit
    
    try:
        info = yf.Ticker(ticker).info
    except Exception as e:
        error_str = str(e).lower()
        # Detect yfinance rate-limit errors
        if "rate" in error_str or "429" in error_str or "too many requests" in error_str:
            _rate_limit_hit = True
            logger.debug(f"YFinance rate-limited, falling back to Finnhub for {ticker}: {e}")
            # Fall through to Finnhub below
            return fetch_finnhub_fundamentals(ticker)
        return None

    if not info:
        # If yfinance returned empty, try Finnhub as fallback
        return fetch_finnhub_fundamentals(ticker)

    market_cap = _safe_float(info.get("marketCap"))
    enterprise_value = _safe_float(info.get("enterpriseValue"))

    roe = _safe_float(info.get("returnOnEquity"))
    roa = _safe_float(info.get("returnOnAssets"))
    margin_gross = _safe_float(info.get("grossMargins"))
    margin_ebit = _safe_float(info.get("operatingMargins"))
    margin_net = _safe_float(info.get("profitMargins"))

    revenue_growth = _safe_float(info.get("revenueGrowth"))
    eps_growth = _safe_float(info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth"))
    ebitda_growth = _safe_float(info.get("earningsGrowth"))

    payout_ratio = _safe_float(info.get("payoutRatio"))
    dividend_yield = _safe_float(info.get("dividendYield"))

    debt_equity = _safe_float(info.get("debtToEquity"))
    current_ratio = _safe_float(info.get("currentRatio"))
    quick_ratio = _safe_float(info.get("quickRatio"))

    fcf = _safe_float(info.get("freeCashflow"))
    fcf_yield = None
    if fcf and market_cap and market_cap > 0:
        fcf_yield = (fcf / market_cap) * 100

    return {
        "market_cap": (market_cap / 1e9) if market_cap else None,
        "enterprise_value": (enterprise_value / 1e9) if enterprise_value else None,
        "per": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
        "peg": _safe_float(info.get("pegRatio")),
        "pbr": _safe_float(info.get("priceToBook")),
        "ps_ratio": _safe_float(info.get("priceToSalesTrailing12Months")),
        "ev_ebitda": _safe_float(info.get("enterpriseToEbitda")),
        "ev_sales": _safe_float(info.get("enterpriseToRevenue")),
        "dividend_yield": (dividend_yield * 100) if dividend_yield is not None else None,
        "payout_ratio": (payout_ratio * 100) if payout_ratio is not None else None,
        "roe": (roe * 100) if roe is not None else None,
        "roa": (roa * 100) if roa is not None else None,
        "roic": None,
        "margin_ebit": (margin_ebit * 100) if margin_ebit is not None else None,
        "margin_net": (margin_net * 100) if margin_net is not None else None,
        "margin_gross": (margin_gross * 100) if margin_gross is not None else None,
        "revenue_growth": (revenue_growth * 100) if revenue_growth is not None else None,
        "eps_growth": (eps_growth * 100) if eps_growth is not None else None,
        "ebitda_growth": (ebitda_growth * 100) if ebitda_growth is not None else None,
        "net_debt_ebitda": None,
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "debt_equity": (debt_equity / 100) if debt_equity is not None else None,
        "fcf_yield": fcf_yield,
    }


async def enrich_fundamentals(
    db: AsyncSession,
    limit: int = 120,
    only_missing: bool = True,
    aggressive: bool = False,
    fallback_provider: str = "finnhub",
) -> dict:
    """
    Enrich fundamental fields for stocks currently in DB.

    aggressive=True: higher concurrency and shorter pause between batches.
    fallback_provider: "finnhub" (free) or "none" (yfinance only)
    """
    global _rate_limit_hit
    _rate_limit_hit = False
    
    query = select(Stock).order_by(Stock.id)

    if only_missing:
        query = query.where(
            or_(
                Stock.per.is_(None),
                Stock.pbr.is_(None),
                Stock.roe.is_(None),
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
            "fallback_used": False,
        }

    batch_size = 12 if aggressive else 6
    pause_seconds = 0.15 if aggressive else 0.7

    loop = asyncio.get_event_loop()
    enriched_rows = 0
    fields_written = 0
    fallback_used = False

    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        tasks = [
            loop.run_in_executor(_executor, _fetch_fundamental_snapshot, stock.ticker)
            for stock in chunk
        ]
        snapshots = await asyncio.gather(*tasks, return_exceptions=True)

        for stock, snap in zip(chunk, snapshots):
            if isinstance(snap, Exception) or not snap:
                continue

            wrote_this_row = False
            for field, value in snap.items():
                if value is None:
                    continue
                current = getattr(stock, field)
                if current is None or (field == "market_cap" and (current or 0) <= 0):
                    setattr(stock, field, round(value, 4) if isinstance(value, float) else value)
                    fields_written += 1
                    wrote_this_row = True
            if wrote_this_row:
                enriched_rows += 1

        # If yfinance rate-limit hit, reduce pause for Finnhub requests
        if _rate_limit_hit:
            fallback_used = True
            pause_seconds = 0.5 if aggressive else 1.0
        
        if i + batch_size < len(rows):
            await asyncio.sleep(pause_seconds)

    await db.commit()

    result_dict = {
        "updated": enriched_rows > 0,
        "checked": len(rows),
        "enriched": enriched_rows,
        "fields_written": fields_written,
        "aggressive": aggressive,
        "only_missing": only_missing,
        "limit": limit,
        "fallback_used": fallback_used,
    }
    
    if fallback_used:
        logger.info(f"📘 Fundamentals enrichment used Finnhub fallback: {enriched_rows} enriched, {fields_written} fields")
    
    return result_dict
