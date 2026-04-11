"""
Market Screener — FastAPI Application
Stock screening API with AI analysis. Zone Bourse augmenté par IA.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func

from app.config import settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.fundamentals_refresh import enrich_fundamentals
from app.models import Stock
from app.pipeline_refresh import run_multi_pass_refresh
from app.seed import generate_identity_only_stocks
from app.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle:
    - Startup: Initialize DB, seed data
    - Shutdown: Close connections gracefully
    """
    # Startup
    logger.info("🚀 Starting Market Screener API...")
    app.state.startup_topup_task = None
    app.state.fundamentals_task = None
    try:
        await init_db()
        logger.info("✅ Database initialized")
        
        # Multi-source refresh with local metric enrichment.
        async with AsyncSessionLocal() as session:
            refresh_result = await run_multi_pass_refresh(
                db=session,
                min_required=settings.startup_min_required,
                fetch_min_valid=settings.startup_fetch_min_valid,
                region="world",
                include_alpaca_fallback=settings.startup_include_alpaca_fallback,
                provider_retries=settings.startup_provider_retries,
                provider_retry_delay_seconds=settings.startup_provider_retry_delay_seconds,
                enable_technical_fallback=settings.startup_enable_technical_fallback,
            )

            count = (await session.execute(select(func.count(Stock.id)))).scalar() or 0
            if refresh_result["updated"]:
                logger.info(
                    "📡 Multi-pass refresh applied: %s valid stocks (source=%s, fetched=%s)",
                    refresh_result["valid"],
                    refresh_result.get("source"),
                    refresh_result["fetched"],
                )
            else:
                logger.warning(
                    "⚠️ Multi-pass refresh not applied: %s (valid=%s, fetched=%s)",
                    refresh_result.get("reason"),
                    refresh_result.get("valid"),
                    refresh_result.get("fetched"),
                )

            if count == 0:
                logger.warning(
                    "⚠️ No valid market data at startup, loading identity-only stock universe"
                )
                session.add_all(generate_identity_only_stocks())
                await session.commit()
                count = (await session.execute(select(func.count(Stock.id)))).scalar() or 0

            logger.info("📊 Database now contains %s stocks", count)

        async def _startup_topup() -> None:
            """Background top-up passes to recover more rows after API is ready."""
            for round_idx in range(1, settings.startup_topup_rounds + 1):
                await asyncio.sleep(settings.startup_topup_interval_seconds)
                try:
                    async with AsyncSessionLocal() as bg_session:
                        refresh_result = await run_multi_pass_refresh(
                            db=bg_session,
                            min_required=settings.startup_min_required,
                            fetch_min_valid=settings.startup_fetch_min_valid,
                            region="world",
                            include_alpaca_fallback=settings.startup_include_alpaca_fallback,
                            provider_retries=settings.startup_provider_retries,
                            provider_retry_delay_seconds=settings.startup_provider_retry_delay_seconds,
                            enable_technical_fallback=settings.startup_enable_technical_fallback,
                        )
                        bg_count = (await bg_session.execute(select(func.count(Stock.id)))).scalar() or 0
                        logger.info(
                            "🔁 Startup top-up pass %s/%s: updated=%s fetched=%s valid=%s total=%s",
                            round_idx,
                            settings.startup_topup_rounds,
                            refresh_result.get("updated"),
                            refresh_result.get("fetched"),
                            refresh_result.get("valid"),
                            bg_count,
                        )
                        if bg_count >= settings.startup_fetch_min_valid:
                            logger.info("✅ Top-up reached target (%s rows)", bg_count)
                            break
                except Exception as exc:
                    logger.warning("⚠️ Startup top-up pass %s failed: %s", round_idx, exc)

        if count < settings.startup_fetch_min_valid and settings.startup_topup_rounds > 0:
            logger.info(
                "⏳ Scheduling background top-up (%s passes every %.1fs, target=%s)",
                settings.startup_topup_rounds,
                settings.startup_topup_interval_seconds,
                settings.startup_fetch_min_valid,
            )
            app.state.startup_topup_task = asyncio.create_task(_startup_topup())

        async def _fundamentals_daemon() -> None:
            """Aggressive early enrichment, then lighter recurring passes."""
            if settings.fundamentals_bootstrap_initial_delay_seconds > 0:
                await asyncio.sleep(settings.fundamentals_bootstrap_initial_delay_seconds)

            # Bootstrap phase: aggressive rounds shortly after startup.
            for round_idx in range(1, settings.fundamentals_bootstrap_rounds + 1):
                if round_idx > 1:
                    await asyncio.sleep(settings.fundamentals_bootstrap_interval_seconds)
                try:
                    async with AsyncSessionLocal() as f_session:
                        result = await enrich_fundamentals(
                            db=f_session,
                            limit=settings.fundamentals_round_limit,
                            only_missing=settings.fundamentals_only_missing,
                            aggressive=True,
                        )
                        logger.info(
                            "📘 Fundamentals bootstrap %s/%s: enriched=%s fields=%s checked=%s",
                            round_idx,
                            settings.fundamentals_bootstrap_rounds,
                            result.get("enriched"),
                            result.get("fields_written"),
                            result.get("checked"),
                        )
                except Exception as exc:
                    logger.warning("⚠️ Fundamentals bootstrap %s failed: %s", round_idx, exc)

            # Maintenance phase: lighter recurring passes.
            while True:
                await asyncio.sleep(settings.fundamentals_maintenance_interval_seconds)
                try:
                    async with AsyncSessionLocal() as f_session:
                        result = await enrich_fundamentals(
                            db=f_session,
                            limit=settings.fundamentals_round_limit,
                            only_missing=settings.fundamentals_only_missing,
                            aggressive=False,
                        )
                        logger.info(
                            "📘 Fundamentals maintenance: enriched=%s fields=%s checked=%s",
                            result.get("enriched"),
                            result.get("fields_written"),
                            result.get("checked"),
                        )
                except Exception as exc:
                    logger.warning("⚠️ Fundamentals maintenance pass failed: %s", exc)

        if settings.fundamentals_enabled:
            logger.info(
                "📘 Scheduling fundamentals daemon (delay=%.1fs, bootstrap=%s every %.1fs, maintenance every %.1fs)",
                settings.fundamentals_bootstrap_initial_delay_seconds,
                settings.fundamentals_bootstrap_rounds,
                settings.fundamentals_bootstrap_interval_seconds,
                settings.fundamentals_maintenance_interval_seconds,
            )
            app.state.fundamentals_task = asyncio.create_task(_fundamentals_daemon())
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    logger.info("✅ Application ready")
    yield  # App runs here

    # Shutdown
    logger.info("🛑 Shutting down...")
    try:
        startup_task = getattr(app.state, "startup_topup_task", None)
        if startup_task and not startup_task.done():
            startup_task.cancel()
        fundamentals_task = getattr(app.state, "fundamentals_task", None)
        if fundamentals_task and not fundamentals_task.done():
            fundamentals_task.cancel()
        await close_db()
        logger.info("✅ Gracefully shut down")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app with configuration
app = FastAPI(
    title=settings.app_name,
    description=(
        "API de screening d'actions augmenté par IA. "
        "Frère de Market Insights. "
        "Filtrage fondamental, technique, consensus, ESG et scoring IA."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS Middleware ──────────────────────────────────────────────────────────
cors_origins = [
    "http://localhost:3000",      # Frontend production
    "http://127.0.0.1:3000",      # Frontend localhost
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:5173",      # Vite localhost
    "http://localhost:8080",      # Nginx
    "http://127.0.0.1:8080",      # Nginx localhost
]

# Allow all origins in development, restrict in production
if settings.environment != "production":
    cors_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1", tags=["screener"])


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    Returns status and can be used by load balancers and orchestrators.
    """
    try:
        # Verify database connection
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
        return {
            "status": "healthy",
            "service": "market-screener-api",
            "version": settings.app_version,
            "environment": settings.environment,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/", tags=["info"])
async def root():
    """API information and available endpoints."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
        "endpoints": {
            "screen": "POST /api/v1/screen",
            "screen_quick": "GET /api/v1/screen/quick",
            "filters": "GET /api/v1/filters",
            "stock": "GET /api/v1/stock/{ticker}",
            "ai_analyze": "GET /api/v1/ai/analyze/{ticker}",
            "presets": "GET /api/v1/presets",
            "saved_screens": "GET /api/v1/saved-screens",
        },
    }
