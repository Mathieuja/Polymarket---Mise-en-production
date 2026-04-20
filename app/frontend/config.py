from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv_if_available() -> None:
    """Load `.env` for local development if python-dotenv is installed."""

    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    load_dotenv()


_load_dotenv_if_available()


@dataclass(frozen=True)
class Settings:
    app_name: str
    backend_mode: str
    api_url: str


def get_settings() -> Settings:
    app_name = os.getenv("APP_NAME", "Polymarket Paper Trading")
    backend_mode = os.getenv("BACKEND_MODE", "api").strip().lower()
    api_url = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

    if backend_mode not in {"mock", "api"}:
        backend_mode = "mock"

    return Settings(app_name=app_name, backend_mode=backend_mode, api_url=api_url)
