"""
Market Screener — Configuration Module
Handles environment variables and application settings.
"""
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic automatically reads env vars by uppercasing field names.
    """
    # Database URL from env var DATABASE_URL
    database_url: str = "postgresql+asyncpg://screener_user:screener_password_dev@postgres:5432/market_screener"
    
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
    
    @property
    def debug(self) -> bool:
        """Debug mode based on environment."""
        return self.environment == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Load settings once at module import
settings = Settings()
