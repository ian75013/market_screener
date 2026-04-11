"""
Market Screener — Multi-source multi-pass refresh pipeline.

Implements a robust staged refresh:
1) Universe selection
2) Provider fetch (Yahoo primary, Alpaca fallback)
3) Local enrichment for missing/derived metrics
4) Quality gate
5) Upsert in database
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.alpaca_finance import fetch_all_stocks_from_alpaca
from app.config import settings
from app.models import Stock
from app.seed import _is_false_stat_payload
from app.yahoo_finance import STOCK_UNIVERSE, fetch_all_stocks

logger = logging.getLogger(__name__)

REGION_COUNTRIES: dict[str, set[str]] = {
    "north_america": {"USA", "Canada"},
    "europe": {
        "France", "Allemagne", "UK", "Suisse", "Pays-Bas", "Italie", "Espagne", "Danemark",
    },
    "asia_pacific": {"Japon", "Corée du Sud", "Inde", "Australie", "Taïwan"},
    "world": set(),
}


def _normalize_region(region: str | None) -> str:
    if not region:
        return "world"
    return region.strip().lower().replace("-", "_")


def _filter_by_region(payloads: Iterable[dict], region: str) -> list[dict]:
    if region == "world":
        return list(payloads)

    allowed = REGION_COUNTRIES.get(region)
    if not allowed:
        return list(payloads)

    return [p for p in payloads if p.get("country") in allowed]


def _enrich_local_metrics(payload: dict) -> dict:
    """Fill stable derived fields locally when provider payloads are sparse."""
    price = payload.get("price")
    high_52w = payload.get("high_52w")
    low_52w = payload.get("low_52w")

    if payload.get("upside") is None and payload.get("target_price") and price and price > 0:
        payload["upside"] = round((payload["target_price"] - price) / price * 100, 1)

    # Keep dist_mm fields consistent whenever one side is missing.
    if payload.get("dist_mm50") is None and payload.get("dist_mm200") is not None:
        payload["dist_mm50"] = round(payload["dist_mm200"] * 0.6, 2)

    # Ensure defensive defaults for numeric non-null columns.
    if payload.get("market_cap") is None:
        payload["market_cap"] = 0.0
    if payload.get("dividend_yield") is None:
        payload["dividend_yield"] = 0.0

    # Guard against malformed 52w bounds.
    if price and high_52w and low_52w and low_52w > high_52w:
        payload["high_52w"], payload["low_52w"] = low_52w, high_52w

    return payload


def _safe_num(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_technical_fallback(payload: dict) -> dict:
    """Compute missing technical indicators from available momentum/price fields."""
    c1m = _safe_num(payload.get("change_1m"))
    c3m = _safe_num(payload.get("change_3m"))
    c6m = _safe_num(payload.get("change_6m"))
    c1y = _safe_num(payload.get("change_1y"))
    high_52w = _safe_num(payload.get("high_52w"))
    low_52w = _safe_num(payload.get("low_52w"))
    price = _safe_num(payload.get("price"))

    # Fill missing momentum buckets from adjacent windows when possible.
    if payload.get("change_3m") is None and c1m is not None and c6m is not None:
        payload["change_3m"] = round((2 * c1m + c6m) / 3, 2)
        c3m = _safe_num(payload.get("change_3m"))

    if payload.get("change_6m") is None and c3m is not None and c1y is not None:
        payload["change_6m"] = round((c3m + c1y) / 2, 2)
        c6m = _safe_num(payload.get("change_6m"))

    # RSI proxy from momentum regime when RSI is unavailable.
    if payload.get("rsi") is None:
        momentum = c1m if c1m is not None else c3m
        if momentum is not None:
            proxy_rsi = 50 + momentum * 1.2
            payload["rsi"] = round(max(5.0, min(95.0, proxy_rsi)), 1)

    # Distances to moving averages from available performance windows.
    if payload.get("dist_mm50") is None and c3m is not None:
        payload["dist_mm50"] = round(max(-40.0, min(40.0, c3m * 0.7)), 2)

    if payload.get("dist_mm200") is None and c6m is not None:
        payload["dist_mm200"] = round(max(-60.0, min(60.0, c6m * 0.8)), 2)

    # Volatility proxy from return dispersion windows.
    if payload.get("volatility") is None:
        components = [abs(x) for x in (c1m, c3m, c6m) if x is not None]
        if components:
            payload["volatility"] = round(max(8.0, min(120.0, sum(components) / len(components) * 1.6)), 2)

    # Ensure 52w bounds are coherent even when partially missing.
    if price is not None and price > 0:
        if high_52w is None:
            payload["high_52w"] = round(price * 1.12, 2)
        if low_52w is None:
            payload["low_52w"] = round(price * 0.88, 2)

    return payload


async def _fetch_provider_with_retries(
    min_required: int,
    fetch_min_valid: int,
    region_key: str,
    include_alpaca_fallback: bool,
    provider_retries: int,
    provider_retry_delay_seconds: float,
) -> tuple[str, list[dict], int]:
    """Fetch provider data with retries and fallback provider escalation."""
    by_ticker: dict[str, dict] = {}
    source = "yahoo"
    attempts = 0

    for i in range(max(1, provider_retries)):
        attempts += 1
        yahoo_payloads = await fetch_all_stocks(
            min_valid=fetch_min_valid,
            ticker_offset=i * 11,
        )
        yahoo_payloads = _filter_by_region(yahoo_payloads, region_key)
        for payload in yahoo_payloads:
            ticker = payload.get("ticker")
            if ticker:
                by_ticker[ticker] = payload
        source = "yahoo"
        if len(by_ticker) >= fetch_min_valid:
            return source, list(by_ticker.values()), attempts
        if i < provider_retries - 1:
            logger.info(
                "⏸️ Startup pass %s/%s complete (%s rows), waiting %.1fs before next pass",
                i + 1,
                provider_retries,
                len(by_ticker),
                provider_retry_delay_seconds,
            )
            await asyncio.sleep(provider_retry_delay_seconds)

    if include_alpaca_fallback and settings.alpaca_api_key and settings.alpaca_secret_key:
        for i in range(max(1, provider_retries)):
            attempts += 1
            alpaca_payloads = await fetch_all_stocks_from_alpaca(min_valid=fetch_min_valid)
            alpaca_payloads = _filter_by_region(alpaca_payloads, region_key)
            for payload in alpaca_payloads:
                ticker = payload.get("ticker")
                if ticker:
                    by_ticker[ticker] = payload
            source = "alpaca"
            if len(by_ticker) >= fetch_min_valid:
                return source, list(by_ticker.values()), attempts
            if i < provider_retries - 1:
                logger.info(
                    "⏸️ Alpaca pass %s/%s complete (%s rows), waiting %.1fs before next pass",
                    i + 1,
                    provider_retries,
                    len(by_ticker),
                    provider_retry_delay_seconds,
                )
                await asyncio.sleep(provider_retry_delay_seconds)

    return source, list(by_ticker.values()), attempts


async def run_multi_pass_refresh(
    db: AsyncSession,
    min_required: int = 20,
    fetch_min_valid: int | None = None,
    region: str | None = None,
    include_alpaca_fallback: bool = True,
    provider_retries: int = 3,
    provider_retry_delay_seconds: float = 2.0,
    enable_technical_fallback: bool = True,
) -> dict:
    """
    Execute a multi-pass refresh and replace stocks table on success.

    Returns stage timings and quality stats for orchestration and monitoring.
    """
    started = time.perf_counter()
    region_key = _normalize_region(region)
    fetch_target = max(min_required, fetch_min_valid or min_required)

    # Pass 1: universe
    t0 = time.perf_counter()
    known_regions = set(REGION_COUNTRIES.keys())
    if region_key not in known_regions:
        region_key = "world"

    universe = STOCK_UNIVERSE
    if region_key != "world":
        allowed = REGION_COUNTRIES[region_key]
        universe = [m for m in STOCK_UNIVERSE if m[2] in allowed]
    pass_universe_ms = round((time.perf_counter() - t0) * 1000, 1)

    # Pass 2: provider fetch (Yahoo primary, then Alpaca fallback)
    t1 = time.perf_counter()
    provider_source, provider_payloads, provider_attempts = await _fetch_provider_with_retries(
        min_required=min_required,
        fetch_min_valid=fetch_target,
        region_key=region_key,
        include_alpaca_fallback=include_alpaca_fallback,
        provider_retries=provider_retries,
        provider_retry_delay_seconds=provider_retry_delay_seconds,
    )
    pass_provider_ms = round((time.perf_counter() - t1) * 1000, 1)

    # Pass 3: local enrichment
    t2 = time.perf_counter()
    enriched = []
    for p in provider_payloads:
        payload = _enrich_local_metrics(dict(p))
        if enable_technical_fallback:
            payload = _apply_technical_fallback(payload)
        enriched.append(payload)
    pass_local_calc_ms = round((time.perf_counter() - t2) * 1000, 1)

    # Pass 4: quality gate
    t3 = time.perf_counter()
    valid_payloads = [p for p in enriched if not _is_false_stat_payload(p)]
    by_ticker: dict[str, dict] = {}
    for payload in valid_payloads:
        ticker = payload.get("ticker")
        if ticker:
            by_ticker[ticker] = payload
    valid_payloads = list(by_ticker.values())
    pass_quality_ms = round((time.perf_counter() - t3) * 1000, 1)

    if len(valid_payloads) < min_required:
        return {
            "updated": False,
            "reason": "not_enough_valid_rows",
            "source": provider_source,
            "provider_attempts": provider_attempts,
            "region": region_key,
            "min_required": min_required,
            "fetch_target": fetch_target,
            "fetched": len(provider_payloads),
            "valid": len(valid_payloads),
            "universe_size": len(universe),
            "timings_ms": {
                "universe": pass_universe_ms,
                "provider": pass_provider_ms,
                "local_calc": pass_local_calc_ms,
                "quality": pass_quality_ms,
                "total": round((time.perf_counter() - started) * 1000, 1),
            },
        }

    # Pass 5: upsert (replace strategy)
    t4 = time.perf_counter()
    await db.execute(delete(Stock))
    db.add_all([Stock(**payload) for payload in valid_payloads])
    await db.commit()
    pass_upsert_ms = round((time.perf_counter() - t4) * 1000, 1)

    return {
        "updated": True,
        "source": provider_source,
        "provider_attempts": provider_attempts,
        "region": region_key,
        "min_required": min_required,
        "fetch_target": fetch_target,
        "fetched": len(provider_payloads),
        "valid": len(valid_payloads),
        "universe_size": len(universe),
        "timings_ms": {
            "universe": pass_universe_ms,
            "provider": pass_provider_ms,
            "local_calc": pass_local_calc_ms,
            "quality": pass_quality_ms,
            "upsert": pass_upsert_ms,
            "total": round((time.perf_counter() - started) * 1000, 1),
        },
    }
