from __future__ import annotations

from app.utils.api_client import APIClient


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
