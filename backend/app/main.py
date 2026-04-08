"""
Market Screener — FastAPI Application
Stock screening API with AI analysis. Zone Bourse augmenté par IA.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func

from app.config import settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.models import Stock
from app.seed import refresh_stocks_from_yahoo
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
    try:
        await init_db()
        logger.info("✅ Database initialized")
        
        # Always prioritize real open market data from Yahoo Finance.
        async with AsyncSessionLocal() as session:
            refresh_result = await refresh_stocks_from_yahoo(
                session,
                min_required=20,
                wipe_if_false_stats=True,
            )

            count = (await session.execute(select(func.count(Stock.id)))).scalar() or 0
            if refresh_result["updated"]:
                logger.info(
                    "📡 Yahoo refresh applied: %s valid stocks (fetched=%s)",
                    refresh_result["valid"],
                    refresh_result["fetched"],
                )
            else:
                logger.warning(
                    "⚠️ Yahoo refresh not applied: %s (valid=%s, fetched=%s)",
                    refresh_result.get("reason"),
                    refresh_result.get("valid"),
                    refresh_result.get("fetched"),
                )

            if count == 0:
                raise RuntimeError("No valid market data available after Yahoo refresh")

            logger.info("📊 Database now contains %s stocks", count)
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    logger.info("✅ Application ready")
    yield  # App runs here

    # Shutdown
    logger.info("🛑 Shutting down...")
    try:
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
