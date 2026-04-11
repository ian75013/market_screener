"""
Market Screener — Configuration Module
Handles environment variables and application settings.
"""
from urllib.parse import quote_plus
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic automatically reads env vars by uppercasing field names.
    """
    # Optional full DSN override from env var DATABASE_URL
    database_url: str | None = None
    # Canonical postgres variables used to build DSN when DATABASE_URL is not set.
    postgres_db: str = "market_screener"
    postgres_user: str = "screener_user"
    postgres_password: str = "screener_password_dev"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    
    # Environment from env var ENVIRONMENT
    environment: Literal["development", "staging", "production"] = "development"
    
    # Server
    app_name: str = "Market Screener API"
    app_version: str = "1.0.0"
    
    # CORS
    frontend_url: str = "http://localhost:3000"

    # Optional provider fallback (Alpaca Data API)
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_data_base_url: str = "https://data.alpaca.markets"

    # Startup refresh tuning (keep boot light on small machines/VPS)
    startup_min_required: int = 8
    startup_fetch_min_valid: int = 40
    startup_provider_retries: int = 1
    startup_provider_retry_delay_seconds: float = 1.0
    startup_include_alpaca_fallback: bool = True
    startup_enable_technical_fallback: bool = True
    startup_topup_rounds: int = 4
    startup_topup_interval_seconds: float = 90.0

    # Dedicated fundamentals enrichment schedule
    fundamentals_enabled: bool = True
    fundamentals_bootstrap_rounds: int = 6
    fundamentals_bootstrap_initial_delay_seconds: float = 300.0
    fundamentals_bootstrap_interval_seconds: float = 120.0
    fundamentals_maintenance_interval_seconds: float = 1800.0
    fundamentals_round_limit: int = 120
    fundamentals_only_missing: bool = True
    
    @property
    def debug(self) -> bool:
        """Debug mode based on environment."""
        return self.environment == "development"

    @property
    def database_url_resolved(self) -> str:
        """Return DATABASE_URL if provided, else build it from POSTGRES_* vars."""
        if self.database_url:
            return self.database_url
        encoded_password = quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Load settings once at module import
settings = Settings()
