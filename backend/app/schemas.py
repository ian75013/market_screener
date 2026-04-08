"""
Market Screener — Pydantic Schemas
Request/response models for the screening API.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class SortDir(str, Enum):
    asc = "asc"
    desc = "desc"


# ── Range filter ─────────────────────────────────────────────────────────────

class RangeFilter(BaseModel):
    """Min/max range for numeric screening."""
    min: Optional[float] = None
    max: Optional[float] = None


# ── Screening Request ────────────────────────────────────────────────────────

class ScreenRequest(BaseModel):
    """
    Full screening request body — mirrors Zone Bourse stock screener.
    All filters optional; only provided fields are applied.
    """
    # ── Text search
    search: Optional[str] = None

    # ── Categorical filters
    country: Optional[str] = None
    countries: Optional[list[str]] = None  # multi-select
    sector: Optional[str] = None
    sectors: Optional[list[str]] = None
    market_index: Optional[str] = None
    indices: Optional[list[str]] = None
    currency: Optional[str] = None
    ai_signal: Optional[str] = None
    ai_signals: Optional[list[str]] = None

    # ── Range filters (fondamentaux)
    market_cap: Optional[RangeFilter] = None
    per: Optional[RangeFilter] = None
    peg: Optional[RangeFilter] = None
    pbr: Optional[RangeFilter] = None
    ps_ratio: Optional[RangeFilter] = None
    ev_ebitda: Optional[RangeFilter] = None
    ev_sales: Optional[RangeFilter] = None
    dividend_yield: Optional[RangeFilter] = None
    payout_ratio: Optional[RangeFilter] = None

    # ── Range filters (rentabilité)
    roe: Optional[RangeFilter] = None
    roa: Optional[RangeFilter] = None
    roic: Optional[RangeFilter] = None
    margin_ebit: Optional[RangeFilter] = None
    margin_net: Optional[RangeFilter] = None
    margin_gross: Optional[RangeFilter] = None

    # ── Range filters (croissance)
    revenue_growth: Optional[RangeFilter] = None
    eps_growth: Optional[RangeFilter] = None
    ebitda_growth: Optional[RangeFilter] = None

    # ── Range filters (santé financière)
    net_debt_ebitda: Optional[RangeFilter] = None
    current_ratio: Optional[RangeFilter] = None
    quick_ratio: Optional[RangeFilter] = None
    debt_equity: Optional[RangeFilter] = None
    fcf_yield: Optional[RangeFilter] = None
    interest_coverage: Optional[RangeFilter] = None

    # ── Range filters (technique)
    rsi: Optional[RangeFilter] = None
    beta: Optional[RangeFilter] = None
    volatility: Optional[RangeFilter] = None
    volume_avg: Optional[RangeFilter] = None
    dist_mm50: Optional[RangeFilter] = None
    dist_mm200: Optional[RangeFilter] = None

    # ── Range filters (performance)
    change_1d: Optional[RangeFilter] = None
    change_1w: Optional[RangeFilter] = None
    change_1m: Optional[RangeFilter] = None
    change_ytd: Optional[RangeFilter] = None
    change_1y: Optional[RangeFilter] = None

    # ── Range filters (analystes & ESG)
    analyst_rating: Optional[RangeFilter] = None
    upside: Optional[RangeFilter] = None
    esg_score: Optional[RangeFilter] = None

    # ── Range filters (IA)
    ai_score_overall: Optional[RangeFilter] = None
    ai_score_fundamental: Optional[RangeFilter] = None
    ai_score_technical: Optional[RangeFilter] = None

    # ── Sorting & Pagination
    sort_by: str = Field(default="market_cap", description="Column to sort by")
    sort_dir: SortDir = Field(default=SortDir.desc)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


# ── Screening Response ───────────────────────────────────────────────────────

class AIScores(BaseModel):
    overall: Optional[float] = None
    fundamental: Optional[float] = None
    technical: Optional[float] = None
    momentum: Optional[float] = None
    risk: Optional[float] = None


class StockResponse(BaseModel):
    id: int
    name: str
    ticker: str
    country: str
    sector: str
    index: str
    currency: str
    isin: Optional[str] = None
    # Price
    price: float
    change1d: float
    change1w: float
    change1m: float
    change3m: Optional[float] = None
    change6m: Optional[float] = None
    changeYTD: float
    change1y: Optional[float] = None
    high52w: Optional[float] = None
    low52w: Optional[float] = None
    # Valuation
    marketCap: float
    enterpriseValue: Optional[float] = None
    per: Optional[float] = None
    peg: Optional[float] = None
    pbr: Optional[float] = None
    psRatio: Optional[float] = None
    evEbitda: Optional[float] = None
    evSales: Optional[float] = None
    # Dividends
    dividendYield: float
    payoutRatio: Optional[float] = None
    # Profitability
    roe: Optional[float] = None
    roa: Optional[float] = None
    roic: Optional[float] = None
    marginEbit: Optional[float] = None
    marginNet: Optional[float] = None
    marginGross: Optional[float] = None
    # Growth
    revenueGrowth: Optional[float] = None
    epsGrowth: Optional[float] = None
    ebitdaGrowth: Optional[float] = None
    # Financial health
    netDebtEbitda: Optional[float] = None
    currentRatio: Optional[float] = None
    quickRatio: Optional[float] = None
    debtEquity: Optional[float] = None
    fcfYield: Optional[float] = None
    interestCoverage: Optional[float] = None
    # Technical
    rsi: Optional[float] = None
    distMM50: Optional[float] = None
    distMM200: Optional[float] = None
    beta: Optional[float] = None
    volatility: Optional[float] = None
    volume: Optional[float] = None
    # Analysts & ESG
    analystRating: Optional[float] = None
    analystCount: Optional[int] = None
    targetPrice: Optional[float] = None
    upside: Optional[float] = None
    esgScore: Optional[float] = None
    esgEnv: Optional[float] = None
    esgSocial: Optional[float] = None
    esgGov: Optional[float] = None
    # AI
    aiScores: AIScores
    aiSignal: Optional[str] = None
    # Meta
    updatedAt: Optional[str] = None


class ScreenResponse(BaseModel):
    """Paginated screening results."""
    stocks: list[StockResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters_applied: int
    sort_by: str
    sort_dir: str


class FilterOptions(BaseModel):
    """Available filter values for dropdowns."""
    countries: list[str]
    sectors: list[str]
    indices: list[str]
    currencies: list[str]
    ai_signals: list[str]
    total_stocks: int
    # Range boundaries for sliders
    ranges: dict[str, dict[str, Optional[float]]]


# ── AI Analysis ──────────────────────────────────────────────────────────────

class AIAnalysisRequest(BaseModel):
    ticker: str


class AIAnalysisResponse(BaseModel):
    ticker: str
    name: str
    signal: str
    scores: AIScores
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    catalysts: list[str]
    risks: list[str]
    key_metrics: dict[str, str]


# ── Saved Screens ────────────────────────────────────────────────────────────

class SavedScreenCreate(BaseModel):
    name: str
    description: Optional[str] = None
    filters: dict = {}
    sort_key: str = "market_cap"
    sort_dir: str = "desc"
    view_preset: str = "performance"


class SavedScreenResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    filters: dict
    sort_key: str
    sort_dir: str
    view_preset: str
    created_at: str
    updated_at: str
