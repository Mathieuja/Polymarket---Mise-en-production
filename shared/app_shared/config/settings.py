"""
Application settings and configuration.

Reads configuration from environment variables with sensible defaults.
Compatible with .env files via python-dotenv.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings.

    Each attribute maps to an environment variable (case-insensitive).
    """

    # Database
    database_url: str = "postgresql+psycopg://polymarket_user:polymarket_password@db:5432/polymarket_db"

    # Polymarket API
    gamma_url: str = "https://gamma-api.polymarket.com"
    clob_url: str = "https://clob.polymarket.com"
    data_url: str = "https://data-api.polymarket.com"
    polymarket_api_key: str | None = None

    # Application
    app_name: str = "Polymarket Paper Trading"
    backend_mode: str = "production"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False
