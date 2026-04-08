"""
Market Screener — API Routes
All endpoints for the screening application.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Stock, SavedScreen
from app.schemas import (
    ScreenRequest, ScreenResponse, StockResponse, FilterOptions,
    AIAnalysisRequest, AIAnalysisResponse,
    SavedScreenCreate, SavedScreenResponse,
)
from app.screener import screen_stocks, get_filter_options, get_stock_by_ticker, get_stock_by_id
from app.ai_analysis import generate_ai_analysis
from app.seed import refresh_stocks_from_yahoo
from sqlalchemy import select, func
import math

router = APIRouter()


# ── Screening ────────────────────────────────────────────────────────────────

@router.post("/screen", response_model=ScreenResponse)
async def screen(req: ScreenRequest, db: AsyncSession = Depends(get_db)):
    """
    Main screening endpoint — Zone Bourse style.
    POST body contains all filters, sorting, and pagination.
    Returns paginated results with total count.
    """
    stocks, total, filters_applied = await screen_stocks(db, req)

    total_pages = math.ceil(total / req.page_size) if total > 0 else 1

    return ScreenResponse(
        stocks=[StockResponse(**s.to_dict()) for s in stocks],
        total=total,
        page=req.page,
        page_size=req.page_size,
        total_pages=total_pages,
        filters_applied=filters_applied,
        sort_by=req.sort_by,
        sort_dir=req.sort_dir.value,
    )


@router.get("/screen/quick", response_model=ScreenResponse)
async def screen_quick(
    search: str = Query(None, description="Text search"),
    country: str = Query(None),
    sector: str = Query(None),
    market_index: str = Query(None),
    ai_signal: str = Query(None),
    sort_by: str = Query("market_cap"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    GET-based screening for simple queries.
    For advanced range filters, use POST /screen.
    """
    from app.schemas import SortDir
    req = ScreenRequest(
        search=search,
        country=country,
        sector=sector,
        market_index=market_index,
        ai_signal=ai_signal,
        sort_by=sort_by,
        sort_dir=SortDir(sort_dir),
        page=page,
        page_size=page_size,
    )
    stocks, total, filters_applied = await screen_stocks(db, req)
    total_pages = math.ceil(total / req.page_size) if total > 0 else 1

    return ScreenResponse(
        stocks=[StockResponse(**s.to_dict()) for s in stocks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        filters_applied=filters_applied,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


# ── Filter Options ───────────────────────────────────────────────────────────

@router.get("/filters", response_model=FilterOptions)
async def filters(db: AsyncSession = Depends(get_db)):
    """
    Returns available filter values and ranges.
    Frontend uses this to populate dropdowns and slider min/max.
    """
    opts = await get_filter_options(db)
    return FilterOptions(**opts)


# ── Stock Details ────────────────────────────────────────────────────────────

@router.get("/stock/{ticker}", response_model=StockResponse)
async def get_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    """Get full details for a single stock by ticker."""
    stock = await get_stock_by_ticker(db, ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    return StockResponse(**stock.to_dict())


@router.get("/stock/id/{stock_id}", response_model=StockResponse)
async def get_stock_by_id_route(stock_id: int, db: AsyncSession = Depends(get_db)):
    """Get full details for a single stock by ID."""
    stock = await get_stock_by_id(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock ID {stock_id} not found")
    return StockResponse(**stock.to_dict())


# ── AI Analysis ──────────────────────────────────────────────────────────────

@router.get("/ai/analyze/{ticker}", response_model=AIAnalysisResponse)
async def ai_analyze(ticker: str, db: AsyncSession = Depends(get_db)):
    """
    AI-powered stock analysis.
    Returns scores, summary, strengths/weaknesses, catalysts, risks.
    """
    stock = await get_stock_by_ticker(db, ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    return generate_ai_analysis(stock)


@router.post("/ai/analyze", response_model=AIAnalysisResponse)
async def ai_analyze_post(req: AIAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """POST variant for AI analysis."""
    stock = await get_stock_by_ticker(db, req.ticker)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {req.ticker} not found")
    return generate_ai_analysis(stock)


# ── Prebuilt Screens (like Zone Bourse selections) ───────────────────────────

@router.get("/presets")
async def get_presets():
    """
    Predefined screening strategies, like Zone Bourse 'Sélections Thématiques'.
    """
    return {
        "presets": [
            {
                "id": "top_dividendes",
                "name": "Top Dividendes",
                "description": "Actions avec les meilleurs rendements de dividende",
                "icon": "💰",
                "filters": {
                    "dividend_yield": {"min": 3.0},
                    "payout_ratio": {"max": 80.0},
                    "sort_by": "dividend_yield",
                    "sort_dir": "desc",
                },
            },
            {
                "id": "top_croissance",
                "name": "Top Croissance",
                "description": "Actions à forte croissance du chiffre d'affaires et des bénéfices",
                "icon": "🚀",
                "filters": {
                    "revenue_growth": {"min": 10.0},
                    "eps_growth": {"min": 10.0},
                    "sort_by": "revenue_growth",
                    "sort_dir": "desc",
                },
            },
            {
                "id": "value_investing",
                "name": "Valorisations faibles",
                "description": "Actions sous-évaluées selon les multiples classiques",
                "icon": "🎯",
                "filters": {
                    "per": {"min": 1.0, "max": 15.0},
                    "pbr": {"max": 2.0},
                    "sort_by": "per",
                    "sort_dir": "asc",
                },
            },
            {
                "id": "top_ia",
                "name": "Top Score IA",
                "description": "Actions les mieux notées par notre algorithme IA",
                "icon": "🧠",
                "filters": {
                    "ai_score_overall": {"min": 65.0},
                    "sort_by": "ai_score_overall",
                    "sort_dir": "desc",
                },
            },
            {
                "id": "survendues",
                "name": "Actions survendues",
                "description": "RSI < 30 — potentiel de rebond technique",
                "icon": "📉",
                "filters": {
                    "rsi": {"max": 30.0},
                    "sort_by": "rsi",
                    "sort_dir": "asc",
                },
            },
            {
                "id": "surachetees",
                "name": "Actions surachetées",
                "description": "RSI > 70 — risque de correction",
                "icon": "📈",
                "filters": {
                    "rsi": {"min": 70.0},
                    "sort_by": "rsi",
                    "sort_dir": "desc",
                },
            },
            {
                "id": "top_esg",
                "name": "Top ESG",
                "description": "Meilleures notations environnementales et sociales",
                "icon": "🌱",
                "filters": {
                    "esg_score": {"min": 65.0},
                    "sort_by": "esg_score",
                    "sort_dir": "desc",
                },
            },
            {
                "id": "big_caps",
                "name": "Mega Caps",
                "description": "Les plus grandes capitalisations mondiales",
                "icon": "🏛️",
                "filters": {
                    "market_cap": {"min": 500.0},
                    "sort_by": "market_cap",
                    "sort_dir": "desc",
                },
            },
            {
                "id": "low_volatility",
                "name": "Faible volatilité",
                "description": "Actions stables avec beta < 0.8",
                "icon": "🛡️",
                "filters": {
                    "beta": {"max": 0.8},
                    "sort_by": "volatility",
                    "sort_dir": "asc",
                },
            },
            {
                "id": "quality",
                "name": "Quality Stocks",
                "description": "ROE élevé, faible endettement, marges solides",
                "icon": "⭐",
                "filters": {
                    "roe": {"min": 15.0},
                    "net_debt_ebitda": {"max": 2.0},
                    "margin_ebit": {"min": 15.0},
                    "sort_by": "roe",
                    "sort_dir": "desc",
                },
            },
        ]
    }


# ── Saved Screens ────────────────────────────────────────────────────────────

@router.get("/saved-screens", response_model=list[SavedScreenResponse])
async def list_saved_screens(db: AsyncSession = Depends(get_db)):
    """List all user-saved screening configurations."""
    result = await db.execute(
        select(SavedScreen).order_by(SavedScreen.updated_at.desc())
    )
    screens = result.scalars().all()
    return [
        SavedScreenResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            filters=json.loads(s.filters_json),
            sort_key=s.sort_key,
            sort_dir=s.sort_dir,
            view_preset=s.view_preset,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in screens
    ]


@router.post("/saved-screens", response_model=SavedScreenResponse)
async def create_saved_screen(req: SavedScreenCreate, db: AsyncSession = Depends(get_db)):
    """Save a screening configuration."""
    screen = SavedScreen(
        name=req.name,
        description=req.description,
        filters_json=json.dumps(req.filters),
        sort_key=req.sort_key,
        sort_dir=req.sort_dir,
        view_preset=req.view_preset,
    )
    db.add(screen)
    await db.commit()
    await db.refresh(screen)
    return SavedScreenResponse(
        id=screen.id,
        name=screen.name,
        description=screen.description,
        filters=json.loads(screen.filters_json),
        sort_key=screen.sort_key,
        sort_dir=screen.sort_dir,
        view_preset=screen.view_preset,
        created_at=screen.created_at.isoformat(),
        updated_at=screen.updated_at.isoformat(),
    )


@router.delete("/saved-screens/{screen_id}")
async def delete_saved_screen(screen_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a saved screen."""
    result = await db.execute(select(SavedScreen).where(SavedScreen.id == screen_id))
    screen = result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Saved screen not found")
    await db.delete(screen)
    await db.commit()
    return {"deleted": True, "id": screen_id}


# ── Stats & Health ───────────────────────────────────────────────────────────

@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    """Dashboard stats for the screener."""
    total = (await db.execute(select(func.count(Stock.id)))).scalar()
    countries = (await db.execute(
        select(func.count(func.distinct(Stock.country)))
    )).scalar()
    sectors = (await db.execute(
        select(func.count(func.distinct(Stock.sector)))
    )).scalar()
    indices = (await db.execute(
        select(func.count(func.distinct(Stock.market_index)))
    )).scalar()

    # Signal distribution
    signal_dist = (await db.execute(
        select(Stock.ai_signal, func.count(Stock.id))
        .group_by(Stock.ai_signal)
        .order_by(func.count(Stock.id).desc())
    )).all()

    # Sector distribution
    sector_dist = (await db.execute(
        select(Stock.sector, func.count(Stock.id))
        .group_by(Stock.sector)
        .order_by(func.count(Stock.id).desc())
    )).all()

    return {
        "total_stocks": total,
        "countries": countries,
        "sectors": sectors,
        "indices": indices,
        "signal_distribution": {row[0]: row[1] for row in signal_dist},
        "sector_distribution": {row[0]: row[1] for row in sector_dist},
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Market Screener API"}


@router.post("/admin/refresh-yahoo")
async def refresh_yahoo_data(
    min_required: int = Query(20, ge=1, le=500),
    wipe_if_false_stats: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Force a refresh from Yahoo Finance and optionally wipe false stats first."""
    result = await refresh_stocks_from_yahoo(
        db,
        min_required=min_required,
        wipe_if_false_stats=wipe_if_false_stats,
    )
    return result
