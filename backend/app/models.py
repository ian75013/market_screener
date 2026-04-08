"""
Market Screener — Database Models
SQLAlchemy ORM models mirroring Zone Bourse screener fields.
"""
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, Index, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Stock(Base):
    """
    Single screened equity with all fundamental, technical, consensus,
    ESG and AI-scoring columns.
    """
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ─────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    country: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    sector: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    market_index: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(5), default="USD")
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Price & Performance ──────────────────────────────────────────
    price: Mapped[float] = mapped_column(Float, nullable=False)
    change_1d: Mapped[float] = mapped_column(Float, default=0.0)
    change_1w: Mapped[float] = mapped_column(Float, default=0.0)
    change_1m: Mapped[float] = mapped_column(Float, default=0.0)
    change_3m: Mapped[float] = mapped_column(Float, default=0.0)
    change_6m: Mapped[float] = mapped_column(Float, default=0.0)
    change_ytd: Mapped[float] = mapped_column(Float, default=0.0)
    change_1y: Mapped[float] = mapped_column(Float, default=0.0)
    high_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_52w: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Valuation (Fondamentaux) ─────────────────────────────────────
    market_cap: Mapped[float] = mapped_column(Float, default=0.0, index=True)  # in Md $
    enterprise_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    per: Mapped[float | None] = mapped_column(Float, nullable=True)  # Price/Earnings
    peg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pbr: Mapped[float | None] = mapped_column(Float, nullable=True)  # Price/Book
    ps_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # Price/Sales
    ev_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_sales: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Dividendes ───────────────────────────────────────────────────
    dividend_yield: Mapped[float] = mapped_column(Float, default=0.0)
    payout_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Rentabilité ──────────────────────────────────────────────────
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roa: Mapped[float | None] = mapped_column(Float, nullable=True)
    roic: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_ebit: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_gross: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Croissance ───────────────────────────────────────────────────
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebitda_growth: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Santé financière ─────────────────────────────────────────────
    net_debt_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    quick_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcf_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Technique ────────────────────────────────────────────────────
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_mm50: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_mm200: Mapped[float | None] = mapped_column(Float, nullable=True)
    beta: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_avg: Mapped[float | None] = mapped_column(Float, nullable=True)  # in millions

    # ── Analystes & ESG ──────────────────────────────────────────────
    analyst_rating: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1-5
    analyst_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    upside: Mapped[float | None] = mapped_column(Float, nullable=True)
    esg_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    esg_env: Mapped[float | None] = mapped_column(Float, nullable=True)
    esg_social: Mapped[float | None] = mapped_column(Float, nullable=True)
    esg_gov: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── AI Scores ────────────────────────────────────────────────────
    ai_score_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_score_fundamental: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_score_technical: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_score_momentum: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_score_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_signal: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Metadata ─────────────────────────────────────────────────────
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_stocks_sector_country", "sector", "country"),
        Index("ix_stocks_ai_score", "ai_score_overall"),
    )

    def to_dict(self) -> dict:
        """Serialize to dict matching frontend expectations."""
        return {
            "id": self.id,
            "name": self.name,
            "ticker": self.ticker,
            "country": self.country,
            "sector": self.sector,
            "index": self.market_index,
            "currency": self.currency,
            "isin": self.isin,
            # Price
            "price": self.price,
            "change1d": self.change_1d,
            "change1w": self.change_1w,
            "change1m": self.change_1m,
            "change3m": self.change_3m,
            "change6m": self.change_6m,
            "changeYTD": self.change_ytd,
            "change1y": self.change_1y,
            "high52w": self.high_52w,
            "low52w": self.low_52w,
            # Valuation
            "marketCap": self.market_cap,
            "enterpriseValue": self.enterprise_value,
            "per": self.per,
            "peg": self.peg,
            "pbr": self.pbr,
            "psRatio": self.ps_ratio,
            "evEbitda": self.ev_ebitda,
            "evSales": self.ev_sales,
            # Dividends
            "dividendYield": self.dividend_yield,
            "payoutRatio": self.payout_ratio,
            # Profitability
            "roe": self.roe,
            "roa": self.roa,
            "roic": self.roic,
            "marginEbit": self.margin_ebit,
            "marginNet": self.margin_net,
            "marginGross": self.margin_gross,
            # Growth
            "revenueGrowth": self.revenue_growth,
            "epsGrowth": self.eps_growth,
            "ebitdaGrowth": self.ebitda_growth,
            # Financial health
            "netDebtEbitda": self.net_debt_ebitda,
            "currentRatio": self.current_ratio,
            "quickRatio": self.quick_ratio,
            "debtEquity": self.debt_equity,
            "fcfYield": self.fcf_yield,
            "interestCoverage": self.interest_coverage,
            # Technical
            "rsi": self.rsi,
            "distMM50": self.dist_mm50,
            "distMM200": self.dist_mm200,
            "beta": self.beta,
            "volatility": self.volatility,
            "volume": self.volume_avg,
            # Analysts & ESG
            "analystRating": self.analyst_rating,
            "analystCount": self.analyst_count,
            "targetPrice": self.target_price,
            "upside": self.upside,
            "esgScore": self.esg_score,
            "esgEnv": self.esg_env,
            "esgSocial": self.esg_social,
            "esgGov": self.esg_gov,
            # AI
            "aiScores": {
                "overall": self.ai_score_overall,
                "fundamental": self.ai_score_fundamental,
                "technical": self.ai_score_technical,
                "momentum": self.ai_score_momentum,
                "risk": self.ai_score_risk,
            },
            "aiSignal": self.ai_signal,
            # Meta
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class SavedScreen(Base):
    """User-saved screening configuration (like Zone Bourse 'Screeners Personnels')."""
    __tablename__ = "saved_screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filters_json: Mapped[str] = mapped_column(String(5000), nullable=False, default="{}")
    sort_key: Mapped[str] = mapped_column(String(50), default="market_cap")
    sort_dir: Mapped[str] = mapped_column(String(4), default="desc")
    view_preset: Mapped[str] = mapped_column(String(30), default="performance")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
