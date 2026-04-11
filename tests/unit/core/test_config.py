from __future__ import annotations

import pytest

from app.frontend.config import get_settings

pytestmark = pytest.mark.unit


def test_get_settings_defaults(monkeypatch):
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("BACKEND_MODE", raising=False)
    monkeypatch.delenv("API_URL", raising=False)

    settings = get_settings()
    assert settings.backend_mode == "mock"
    assert settings.api_url.startswith("http")
    assert settings.app_name


def test_get_settings_normalizes(monkeypatch):
    monkeypatch.setenv("BACKEND_MODE", "API")
    monkeypatch.setenv("API_URL", "http://localhost:8000/")

    settings = get_settings()
    assert settings.backend_mode == "api"
    assert settings.api_url == "http://localhost:8000"
