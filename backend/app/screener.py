"""
Market Screener — Screening Service
Dynamic SQLAlchemy query builder supporting all Zone Bourse-style filters.
"""
from sqlalchemy import select, func, asc, desc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Stock
from app.schemas import ScreenRequest, RangeFilter


REGION_COUNTRIES = {
    "north_america": ["USA", "Canada"],
    "europe": ["France", "Allemagne", "UK", "Suisse", "Pays-Bas", "Italie", "Espagne", "Danemark"],
    "asia_pacific": ["Japon", "Corée du Sud", "Inde", "Australie", "Taïwan"],
    "world": [],
}

MARKET_CAP_BUCKETS_BN = {
    "micro": (0.0, 0.3),
    "small": (0.3, 2.0),
    "mid": (2.0, 10.0),
    "large": (10.0, 200.0),
    "mega": (200.0, None),
}


# ── Column mapping: schema field → ORM column ───────────────────────────────

SORT_COLUMNS = {
    "name": Stock.name,
    "ticker": Stock.ticker,
    "country": Stock.country,
    "sector": Stock.sector,
    "market_index": Stock.market_index,
    "price": Stock.price,
    "change_1d": Stock.change_1d,
    "change_1w": Stock.change_1w,
    "change_1m": Stock.change_1m,
    "change_3m": Stock.change_3m,
    "change_6m": Stock.change_6m,
    "change_ytd": Stock.change_ytd,
    "change_1y": Stock.change_1y,
    "market_cap": Stock.market_cap,
    "enterprise_value": Stock.enterprise_value,
    "per": Stock.per,
    "peg": Stock.peg,
    "pbr": Stock.pbr,
    "ps_ratio": Stock.ps_ratio,
    "ev_ebitda": Stock.ev_ebitda,
    "ev_sales": Stock.ev_sales,
    "dividend_yield": Stock.dividend_yield,
    "payout_ratio": Stock.payout_ratio,
    "roe": Stock.roe,
    "roa": Stock.roa,
    "roic": Stock.roic,
    "margin_ebit": Stock.margin_ebit,
    "margin_net": Stock.margin_net,
    "margin_gross": Stock.margin_gross,
    "revenue_growth": Stock.revenue_growth,
    "eps_growth": Stock.eps_growth,
    "ebitda_growth": Stock.ebitda_growth,
    "net_debt_ebitda": Stock.net_debt_ebitda,
    "current_ratio": Stock.current_ratio,
    "quick_ratio": Stock.quick_ratio,
    "debt_equity": Stock.debt_equity,
    "fcf_yield": Stock.fcf_yield,
    "interest_coverage": Stock.interest_coverage,
    "rsi": Stock.rsi,
    "dist_mm50": Stock.dist_mm50,
    "dist_mm200": Stock.dist_mm200,
    "beta": Stock.beta,
    "volatility": Stock.volatility,
    "volume_avg": Stock.volume_avg,
    "analyst_rating": Stock.analyst_rating,
    "target_price": Stock.target_price,
    "upside": Stock.upside,
    "esg_score": Stock.esg_score,
    "ai_score_overall": Stock.ai_score_overall,
    "ai_score_fundamental": Stock.ai_score_fundamental,
    "ai_score_technical": Stock.ai_score_technical,
    "ai_score_momentum": Stock.ai_score_momentum,
    "ai_score_risk": Stock.ai_score_risk,
}

# Range filter mapping: schema field → ORM column
RANGE_FILTERS = {
    "market_cap": Stock.market_cap,
    "per": Stock.per,
    "peg": Stock.peg,
    "pbr": Stock.pbr,
    "ps_ratio": Stock.ps_ratio,
    "ev_ebitda": Stock.ev_ebitda,
    "ev_sales": Stock.ev_sales,
    "dividend_yield": Stock.dividend_yield,
    "payout_ratio": Stock.payout_ratio,
    "roe": Stock.roe,
    "roa": Stock.roa,
    "roic": Stock.roic,
    "margin_ebit": Stock.margin_ebit,
    "margin_net": Stock.margin_net,
    "margin_gross": Stock.margin_gross,
    "revenue_growth": Stock.revenue_growth,
    "eps_growth": Stock.eps_growth,
    "ebitda_growth": Stock.ebitda_growth,
    "net_debt_ebitda": Stock.net_debt_ebitda,
    "current_ratio": Stock.current_ratio,
    "quick_ratio": Stock.quick_ratio,
    "debt_equity": Stock.debt_equity,
    "fcf_yield": Stock.fcf_yield,
    "interest_coverage": Stock.interest_coverage,
    "rsi": Stock.rsi,
    "beta": Stock.beta,
    "volatility": Stock.volatility,
    "volume_avg": Stock.volume_avg,
    "dist_mm50": Stock.dist_mm50,
    "dist_mm200": Stock.dist_mm200,
    "change_1d": Stock.change_1d,
    "change_1w": Stock.change_1w,
    "change_1m": Stock.change_1m,
    "change_3m": Stock.change_3m,
    "change_6m": Stock.change_6m,
    "change_ytd": Stock.change_ytd,
    "change_1y": Stock.change_1y,
    "analyst_rating": Stock.analyst_rating,
    "upside": Stock.upside,
    "esg_score": Stock.esg_score,
    "ai_score_overall": Stock.ai_score_overall,
    "ai_score_fundamental": Stock.ai_score_fundamental,
    "ai_score_technical": Stock.ai_score_technical,
}

DERIVED_RANGE_FILTERS = {
    # Distance to 52w high/low in percent.
    # dist_52w_high: 0 means at high; 10 means 10% below high.
    "dist_52w_high": ((Stock.high_52w - Stock.price) / func.nullif(Stock.high_52w, 0)) * 100,
    # dist_52w_low: 0 means at low; 10 means 10% above low.
    "dist_52w_low": ((Stock.price - Stock.low_52w) / func.nullif(Stock.low_52w, 0)) * 100,
}


def _apply_range(query, column, rf: RangeFilter):
    """Apply min/max range filter to query."""
    if rf.min is not None:
        query = query.where(column >= rf.min)
    if rf.max is not None:
        query = query.where(column <= rf.max)
    return query


async def screen_stocks(db: AsyncSession, req: ScreenRequest):
    """
    Execute a full screening query. Returns (stocks, total_count, filters_applied).
    """
    query = select(Stock)
    count_query = select(func.count(Stock.id))
    filters_applied = 0

    # ── Text search ──────────────────────────────────────────────────
    if req.search:
        pattern = f"%{req.search}%"
        cond = or_(
            Stock.name.ilike(pattern),
            Stock.ticker.ilike(pattern),
            Stock.isin.ilike(pattern),
        )
        query = query.where(cond)
        count_query = count_query.where(cond)
        filters_applied += 1

    # ── Categorical filters ──────────────────────────────────────────
    cat_filters = [
        ("country", Stock.country, req.country, req.countries),
        ("sector", Stock.sector, req.sector, req.sectors),
        ("market_index", Stock.market_index, req.market_index, req.indices),
        ("ai_signal", Stock.ai_signal, req.ai_signal, req.ai_signals),
    ]
    for name, col, single, multi in cat_filters:
        if multi:
            cond = col.in_(multi)
            query = query.where(cond)
            count_query = count_query.where(cond)
            filters_applied += 1
        elif single:
            cond = col == single
            query = query.where(cond)
            count_query = count_query.where(cond)
            filters_applied += 1

    if req.currency:
        cond = Stock.currency == req.currency
        query = query.where(cond)
        count_query = count_query.where(cond)
        filters_applied += 1

    # Region filter (maps to countries)
    regions: list[str] = []
    if req.regions:
        regions = [r.strip().lower().replace("-", "_") for r in req.regions if r]
    elif req.region:
        regions = [req.region.strip().lower().replace("-", "_")]

    if regions:
        allowed_countries: set[str] = set()
        for region in regions:
            if region in REGION_COUNTRIES and region != "world":
                allowed_countries.update(REGION_COUNTRIES[region])
        if allowed_countries:
            cond = Stock.country.in_(sorted(allowed_countries))
            query = query.where(cond)
            count_query = count_query.where(cond)
            filters_applied += 1

    # Market cap buckets in billion USD-equivalent.
    if req.market_cap_bucket:
        bucket_key = req.market_cap_bucket.strip().lower()
        bounds = MARKET_CAP_BUCKETS_BN.get(bucket_key)
        if bounds:
            lo, hi = bounds
            conds = [Stock.market_cap >= lo]
            if hi is not None:
                conds.append(Stock.market_cap < hi)
            cond = and_(*conds)
            query = query.where(cond)
            count_query = count_query.where(cond)
            filters_applied += 1

    if req.above_mm50 is not None:
        cond = Stock.dist_mm50 >= 0 if req.above_mm50 else Stock.dist_mm50 < 0
        query = query.where(cond)
        count_query = count_query.where(cond)
        filters_applied += 1

    if req.above_mm200 is not None:
        cond = Stock.dist_mm200 >= 0 if req.above_mm200 else Stock.dist_mm200 < 0
        query = query.where(cond)
        count_query = count_query.where(cond)
        filters_applied += 1

    # Near 52w high/low means distance <= 5%.
    dist_52w_high_expr = DERIVED_RANGE_FILTERS["dist_52w_high"]
    dist_52w_low_expr = DERIVED_RANGE_FILTERS["dist_52w_low"]

    if req.near_52w_high is not None:
        cond = dist_52w_high_expr <= 5 if req.near_52w_high else dist_52w_high_expr > 5
        query = query.where(cond)
        count_query = count_query.where(cond)
        filters_applied += 1

    if req.near_52w_low is not None:
        cond = dist_52w_low_expr <= 5 if req.near_52w_low else dist_52w_low_expr > 5
        query = query.where(cond)
        count_query = count_query.where(cond)
        filters_applied += 1

    # ── Range filters ────────────────────────────────────────────────
    for field_name, column in RANGE_FILTERS.items():
        rf: RangeFilter | None = getattr(req, field_name, None)
        if rf is not None and (rf.min is not None or rf.max is not None):
            query = _apply_range(query, column, rf)
            count_query = _apply_range(count_query, column, rf)
            filters_applied += 1

    for field_name, expr in DERIVED_RANGE_FILTERS.items():
        rf: RangeFilter | None = getattr(req, field_name, None)
        if rf is not None and (rf.min is not None or rf.max is not None):
            query = _apply_range(query, expr, rf)
            count_query = _apply_range(count_query, expr, rf)
            filters_applied += 1

    # ── Count total before pagination ────────────────────────────────
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # ── Sorting ──────────────────────────────────────────────────────
    sort_col = SORT_COLUMNS.get(req.sort_by, Stock.market_cap)
    if req.sort_dir.value == "asc":
        query = query.order_by(asc(sort_col).nulls_last())
    else:
        query = query.order_by(desc(sort_col).nulls_last())

    # ── Pagination ───────────────────────────────────────────────────
    offset = (req.page - 1) * req.page_size
    query = query.offset(offset).limit(req.page_size)

    # ── Execute ──────────────────────────────────────────────────────
    result = await db.execute(query)
    stocks = result.scalars().all()

    return stocks, total, filters_applied


async def get_filter_options(db: AsyncSession) -> dict:
    """
    Fetch distinct values for categorical filters and min/max ranges.
    Like Zone Bourse sidebar showing available filter options.
    """
    # Distinct categorical values
    countries = (await db.execute(
        select(Stock.country).distinct().order_by(Stock.country)
    )).scalars().all()

    sectors = (await db.execute(
        select(Stock.sector).distinct().order_by(Stock.sector)
    )).scalars().all()

    indices = (await db.execute(
        select(Stock.market_index).distinct().order_by(Stock.market_index)
    )).scalars().all()

    currencies = (await db.execute(
        select(Stock.currency).distinct().order_by(Stock.currency)
    )).scalars().all()

    signals = (await db.execute(
        select(Stock.ai_signal).distinct().order_by(Stock.ai_signal)
    )).scalars().all()

    total = (await db.execute(select(func.count(Stock.id)))).scalar()

    # Numeric ranges for sliders
    range_cols = {
        "market_cap": Stock.market_cap,
        "per": Stock.per,
        "peg": Stock.peg,
        "pbr": Stock.pbr,
        "ev_ebitda": Stock.ev_ebitda,
        "dividend_yield": Stock.dividend_yield,
        "roe": Stock.roe,
        "roa": Stock.roa,
        "margin_ebit": Stock.margin_ebit,
        "margin_gross": Stock.margin_gross,
        "revenue_growth": Stock.revenue_growth,
        "eps_growth": Stock.eps_growth,
        "net_debt_ebitda": Stock.net_debt_ebitda,
        "current_ratio": Stock.current_ratio,
        "fcf_yield": Stock.fcf_yield,
        "rsi": Stock.rsi,
        "beta": Stock.beta,
        "volatility": Stock.volatility,
        "analyst_rating": Stock.analyst_rating,
        "upside": Stock.upside,
        "esg_score": Stock.esg_score,
        "ai_score_overall": Stock.ai_score_overall,
        "dist_52w_high": DERIVED_RANGE_FILTERS["dist_52w_high"],
        "dist_52w_low": DERIVED_RANGE_FILTERS["dist_52w_low"],
    }

    ranges = {}
    for name, col in range_cols.items():
        result = await db.execute(
            select(func.min(col), func.max(col))
        )
        row = result.one()
        ranges[name] = {"min": row[0], "max": row[1]}

    return {
        "countries": countries,
        "sectors": sectors,
        "indices": indices,
        "currencies": currencies,
        "ai_signals": [s for s in signals if s],
        "total_stocks": total,
        "ranges": ranges,
    }


async def get_stock_by_ticker(db: AsyncSession, ticker: str) -> Stock | None:
    """Fetch a single stock by ticker."""
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    return result.scalar_one_or_none()


async def get_stock_by_id(db: AsyncSession, stock_id: int) -> Stock | None:
    """Fetch a single stock by ID."""
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    return result.scalar_one_or_none()
