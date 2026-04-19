from __future__ import annotations

import pytest

from app.frontend.utils.api_client import APIClient, APIClientError

pytestmark = [pytest.mark.unit, pytest.mark.component]


def test_mock_markets_loads_fixtures():
    api = APIClient(backend_mode="mock", api_url="http://example")
    markets = api.get_markets()

    assert isinstance(markets, list)
    assert len(markets) >= 1
    assert "title" in markets[0]


def test_mock_portfolios_loads_fixtures():
    api = APIClient(backend_mode="mock", api_url="http://example")
    portfolios = api.get_portfolios()

    assert isinstance(portfolios, list)
    assert len(portfolios) >= 1
    assert "cash_usd" in portfolios[0]


def test_mock_register_requires_all_fields():
    api = APIClient(backend_mode="mock", api_url="http://example")

    with pytest.raises(APIClientError):
        api.register(name="", email="demo@example.com", password="secret123")


def test_mock_register_returns_token_payload():
    api = APIClient(backend_mode="mock", api_url="http://example")
    data = api.register(name="Demo", email="demo@example.com", password="secret123")

    assert data["token_type"] == "bearer"
    assert data["email"] == "demo@example.com"
