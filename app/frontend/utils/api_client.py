from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests

from .portfolio_math import can_sell


class APIClientError(RuntimeError):
    pass


@dataclass
class APIClient:
    backend_mode: str
    api_url: str
    timeout_s: float = 10.0

    def _headers(self, token: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # --- Auth ---
    def login(self, email: str, password: str) -> dict[str, Any]:
        if self.backend_mode == "mock":
            if not email.strip() or not password:
                raise APIClientError("Email/password required")
            return {"access_token": "mock-token", "token_type": "bearer", "email": email}

        payload = {"email": email, "password": password}
        return self._post_json("/auth/login", payload)

    def register(self, name: str, email: str, password: str) -> dict[str, Any]:
        if self.backend_mode == "mock":
            if not name.strip() or not email.strip() or not password:
                raise APIClientError("Name/email/password required")
            return {"access_token": "mock-token", "token_type": "bearer", "email": email}

        payload = {"name": name, "email": email, "password": password}
        return self._post_json("/auth/register", payload)

    # --- Read models ---
    def get_markets(self) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            return list(_load_fixture("markets.json"))

        data = self._get_json("/markets")
        if isinstance(data, dict) and "items" in data:
            return list(data["items"])
        if isinstance(data, list):
            return data
        raise APIClientError("Unexpected /markets response")

    def get_portfolios(self, token: str | None = None) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            return list(_mock_portfolios())

        data = self._get_json("/portfolios", token=token)
        if isinstance(data, list):
            return data
        raise APIClientError("Unexpected /portfolios response")

    def get_trades(self, token: str | None = None) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            return list(_mock_trades())

        data = self._get_json("/trades", token=token)
        if isinstance(data, list):
            return data
        raise APIClientError("Unexpected /trades response")

    def create_portfolio(
        self,
        name: str,
        initial_cash_usd: float,
        token: str | None = None,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            portfolio = {
                "id": f"pf-{uuid4().hex[:8]}",
                "name": name.strip() or "Untitled",
                "cash_usd": float(initial_cash_usd),
                "initial_cash_usd": float(initial_cash_usd),
            }
            portfolios = _mock_portfolios()
            portfolios.append(portfolio)
            _set_mock_portfolios(portfolios)
            return portfolio

        payload = {"name": name, "initial_cash_usd": initial_cash_usd}
        return self._post_json("/portfolios", payload, token=token)

    def create_trade(
        self,
        portfolio_id: str,
        market_id: str,
        outcome: str,
        action: str,
        qty: float,
        price: float,
        token: str | None = None,
    ) -> dict[str, Any]:
        outcome = outcome.upper()
        action = action.upper()

        if self.backend_mode == "mock":
            if qty <= 0:
                raise APIClientError("Quantity must be > 0")
            if not (0.0 <= price <= 1.0):
                raise APIClientError("Price must be between 0 and 1")

            portfolios = _mock_portfolios()
            portfolio = next((p for p in portfolios if p.get("id") == portfolio_id), None)
            if not portfolio:
                raise APIClientError("Unknown portfolio")

            cash = float(portfolio.get("cash_usd", 0.0))
            delta_cash = float(qty) * float(price)
            if action == "BUY":
                if cash < delta_cash:
                    raise APIClientError("Insufficient cash")
                cash -= delta_cash
            elif action == "SELL":
                existing_trades = _mock_trades()
                if not can_sell(
                    trades=existing_trades,
                    portfolio_id=portfolio_id,
                    market_id=market_id,
                    outcome=outcome,
                    qty=float(qty),
                ):
                    raise APIClientError("Insufficient position to sell")
                cash += delta_cash
            else:
                raise APIClientError("Action must be BUY or SELL")

            portfolio["cash_usd"] = cash
            _set_mock_portfolios(portfolios)

            trade = {
                "id": f"tr-{uuid4().hex[:8]}",
                "portfolio_id": portfolio_id,
                "market_id": market_id,
                "outcome": outcome,
                "action": action,
                "qty": float(qty),
                "price": float(price),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            trades = _mock_trades()
            trades.append(trade)
            _set_mock_trades(trades)
            return trade

        payload = {
            "portfolio_id": portfolio_id,
            "market_id": market_id,
            "outcome": outcome,
            "action": action,
            "qty": qty,
            "price": price,
        }
        return self._post_json(f"/portfolios/{portfolio_id}/trades", payload, token=token)

    # --- HTTP helpers ---
    def _get_json(self, path: str, token: str | None = None) -> Any:
        url = f"{self.api_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers(token), timeout=self.timeout_s)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise APIClientError(f"GET {path} failed: {exc}") from exc
        except ValueError as exc:
            raise APIClientError(f"GET {path} returned invalid JSON") from exc

    def _post_json(self, path: str, payload: dict[str, Any], token: str | None = None) -> Any:
        url = f"{self.api_url}{path}"
        try:
            resp = requests.post(
                url,
                headers={**self._headers(token), "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            detail = None
            if exc.response is not None:
                try:
                    data = exc.response.json()
                    if isinstance(data, dict):
                        detail = data.get("detail")
                except ValueError:
                    detail = None

            if detail:
                raise APIClientError(str(detail)) from exc
            raise APIClientError(f"POST {path} failed: {exc}") from exc
        except requests.RequestException as exc:
            raise APIClientError(f"POST {path} failed: {exc}") from exc
        except ValueError as exc:
            raise APIClientError(f"POST {path} returned invalid JSON") from exc


@lru_cache(maxsize=32)
def _load_fixture(name: str) -> Any:
    fixtures_dir = Path(__file__).resolve().parents[1] / "configs" / "fixtures"
    path = fixtures_dir / name
    if not path.exists():
        raise APIClientError(f"Missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _mock_portfolios() -> list[dict[str, Any]]:
    import streamlit as st

    value = st.session_state.get("mock_portfolios")
    if value is None:
        return list(_load_fixture("portfolios.json"))
    return list(value)


def _set_mock_portfolios(portfolios: list[dict[str, Any]]) -> None:
    import streamlit as st

    st.session_state.mock_portfolios = portfolios


def _mock_trades() -> list[dict[str, Any]]:
    import streamlit as st

    value = st.session_state.get("mock_trades")
    if value is None:
        return list(_load_fixture("trades.json"))
    return list(value)


def _set_mock_trades(trades: list[dict[str, Any]]) -> None:
    import streamlit as st

    st.session_state.mock_trades = trades
