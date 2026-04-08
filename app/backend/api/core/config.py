"""
Application configuration settings, will contain rate limits, API URLs ...
Later will be loaded from environment variables, this will just be the default.
"""

from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    """"""
    # Polymarket API
    gamma_url: str = "https://gamma-api.polymarket.com"
    clob_url: str = "https://clob.polymarket.com"
    data_url: str = "https://data-api.polymarket.com"
    polymarket_api_key: str | None = None

