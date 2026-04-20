from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
import streamlit as st

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

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200,),
    ) -> Any:
        url = f"{self.api_url}{path}"
        headers = self._headers(token)
        if payload is not None:
            headers = {**headers, "Content-Type": "application/json"}

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=payload,
                timeout=self.timeout_s,
            )
        except requests.RequestException as exc:
            raise APIClientError(f"{method} {path} failed: {exc}") from exc

        if resp.status_code not in expected_statuses:
            detail = None
            try:
                data = resp.json()
                if isinstance(data, dict):
                    detail = data.get("detail")
            except ValueError:
                detail = None

            if resp.status_code == 401:
                raise APIClientError(detail or "Unauthorized request")
            if resp.status_code == 404:
                raise APIClientError("Endpoint not available")
            raise APIClientError(detail or f"{method} {path} failed with {resp.status_code}")

        if not resp.text:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            raise APIClientError(f"{method} {path} returned invalid JSON") from exc

    def _get_json(
        self,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("GET", path, token=token, params=params)

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        token: str | None = None,
        expected_statuses: tuple[int, ...] = (200, 201),
    ) -> Any:
        return self._request(
            "POST",
            path,
            token=token,
            payload=payload,
            expected_statuses=expected_statuses,
        )

    def _delete(
        self,
        path: str,
        *,
        token: str | None = None,
        expected_statuses: tuple[int, ...] = (200, 204),
    ) -> Any:
        return self._request(
            "DELETE",
            path,
            token=token,
            expected_statuses=expected_statuses,
        )

    # -------------------------
    # Auth
    # -------------------------

    def login(self, email: str, password: str) -> dict[str, Any]:
        if self.backend_mode == "mock":
            if not email.strip() or not password:
                raise APIClientError("Email/password required")
            return {"access_token": "mock-token", "token_type": "bearer", "email": email}

        payload = {"email": email, "password": password}
        return self._post_json("/auth/login", payload, expected_statuses=(200,))

    def register(self, name: str, email: str, password: str) -> dict[str, Any]:
        if self.backend_mode == "mock":
            if not name.strip() or not email.strip() or not password:
                raise APIClientError("Name/email/password required")
            return {"access_token": "mock-token", "token_type": "bearer", "email": email}

        payload = {"name": name, "email": email, "password": password}
        return self._post_json("/auth/register", payload)

    def get_me(self, token: str | None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            return {
                "id": "user-mock",
                "email": str(st.session_state.get("user_email") or "demo@local"),
            }
        return self._get_json("/auth/me", token=token)

    def change_password(
        self,
        token: str | None,
        current_password: str,
        new_password: str,
        new_password_confirm: str,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            if not current_password or not new_password or not new_password_confirm:
                raise APIClientError("All password fields are required")
            if new_password != new_password_confirm:
                raise APIClientError("The new passwords do not match")
            return {"status": "ok"}

        payload = {
            "current_password": current_password,
            "new_password": new_password,
            "new_password_confirm": new_password_confirm,
        }
        return self._post_json("/auth/change-password", payload, token=token)

    # -------------------------
    # Markets
    # -------------------------

    def list_markets(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        active: bool | None = None,
        closed: bool | None = None,
        volume_min: float | None = None,
        sort_by: str | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            items = list(_load_fixture("markets.json"))
            if search:
                needle = search.lower()
                items = [
                    m
                    for m in items
                    if needle in str(m.get("question", m.get("title", ""))).lower()
                ]
            if active is True:
                items = [m for m in items if not bool(m.get("closed", False))]
            if closed is True:
                items = [m for m in items if bool(m.get("closed", False))]
            if volume_min is not None:
                items = [
                    m
                    for m in items
                    if float(m.get("volume_24h", m.get("volume", 0.0)) or 0.0) >= volume_min
                ]

            if sort_by == "volume_24h_desc":
                items = sorted(
                    items,
                    key=lambda m: float(m.get("volume_24h", m.get("volume", 0.0)) or 0.0),
                    reverse=True,
                )

            total = len(items)
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            paged = items[start:end]
            total_pages = max(1, (total + page_size - 1) // page_size)
            return {
                "items": paged,
                "total": total,
                "total_pages": total_pages,
                "page": page,
            }

        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if search:
            params["search"] = search
        if active is not None:
            params["active"] = active
        if closed is not None:
            params["closed"] = closed
        if volume_min is not None:
            params["volume_min"] = volume_min
        if sort_by:
            params["sort_by"] = sort_by

        data = self._get_json("/markets", token=token, params=params)
        if isinstance(data, dict) and "markets" in data:
            return {
                "items": data.get("markets", []),
                "total": data.get("total", 0),
                "total_pages": data.get("total_pages", 1),
                "page": data.get("page", page),
            }
        if isinstance(data, list):
            return {
                "items": data,
                "total": len(data),
                "total_pages": 1,
                "page": 1,
            }
        raise APIClientError("Unexpected /markets response")

    def get_markets(self, token: str | None = None) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            return list(_load_fixture("markets.json"))

        listing = self.list_markets(page=1, page_size=100, token=token)
        return list(listing.get("items", []))

    def get_top_markets(
        self,
        *,
        limit: int = 10,
        sort_by: str = "volume_24h",
        token: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            markets = list(_load_fixture("markets.json"))
            if sort_by == "volume_24h":
                markets = sorted(
                    markets,
                    key=lambda m: float(m.get("volume_24h", m.get("volume", 0.0)) or 0.0),
                    reverse=True,
                )
            return markets[:limit]

        data = self._get_json(
            "/markets/top",
            token=token,
            params={"limit": limit, "sort_by": sort_by},
        )
        if isinstance(data, list):
            return data
        raise APIClientError("Unexpected /markets/top response")

    def get_market(self, slug: str, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            for market in _load_fixture("markets.json"):
                candidate_slug = (
                    market.get("slug")
                    or market.get("id")
                    or market.get("condition_id")
                )
                if str(candidate_slug) == str(slug):
                    return market
            raise APIClientError("Market not found")
        return self._get_json(f"/markets/by-slug/{slug}", token=token)

    def get_market_by_condition(
        self,
        condition_id: str,
        token: str | None = None,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            for market in _load_fixture("markets.json"):
                if str(market.get("condition_id")) == str(condition_id):
                    return market
            raise APIClientError("Market not found")
        return self._get_json(f"/markets/by-condition/{condition_id}", token=token)

    def get_price_history(
        self,
        slug: str,
        *,
        outcome_index: int = 0,
        token: str | None = None,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            market = self.get_market(slug)
            prices = market.get("prices")
            if isinstance(prices, list):
                return {"points": prices, "outcome_index": outcome_index}
            return {"points": [], "outcome_index": outcome_index}

        return self._get_json(
            f"/markets/by-slug/{slug}/prices",
            token=token,
            params={"outcome_index": outcome_index},
        )

    def get_sync_stats(self, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            markets = list(_load_fixture("markets.json"))
            return {
                "markets_count": len(markets),
                "status": "mock",
            }
        return self._get_json("/markets/stats", token=token)

    # -------------------------
    # Portfolio / trades
    # -------------------------

    def list_portfolios(self, token: str | None = None) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            return list(_mock_portfolios())

        data = self._get_json("/portfolios", token=token)
        if isinstance(data, list):
            return data
        raise APIClientError("Unexpected /portfolios response")

    def get_portfolios(self, token: str | None = None) -> list[dict[str, Any]]:
        return self.list_portfolios(token=token)

    def create_portfolio(
        self,
        name: str,
        initial_cash_usd: float,
        token: str | None = None,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            return _create_mock_portfolio(name, initial_cash_usd)

        payload = {"name": name, "initial_balance": float(initial_cash_usd)}
        return self._post_json("/portfolios", payload, token=token)

    def get_portfolio(self, portfolio_id: str, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            return _get_mock_portfolio(portfolio_id)

        return self._get_json(f"/portfolios/{portfolio_id}", token=token)

    def get_trades(
        self,
        token: str | None = None,
        *,
        portfolio_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        if self.backend_mode == "mock":
            trades = list(_mock_trades())
            if portfolio_id:
                trades = [t for t in trades if str(t.get("portfolio_id")) == str(portfolio_id)]
            return trades

        if not portfolio_id:
            # Aggregate over all portfolios when backend does not expose /trades.
            trades: list[dict[str, Any]] = []
            for pf in self.list_portfolios(token=token):
                pid = str(pf.get("id") or pf.get("_id") or "")
                if not pid:
                    continue
                trades.extend(
                    self.get_trades(token=token, portfolio_id=pid, page=1, page_size=100)
                )
            return trades

        data = self._get_json(
            f"/portfolios/{portfolio_id}/trades",
            token=token,
            params={"page": page, "page_size": page_size},
        )
        if isinstance(data, dict):
            items = data.get("trades")
            if isinstance(items, list):
                return items
        if isinstance(data, list):
            return data
        raise APIClientError("Unexpected trades response")

    def delete_portfolio(self, portfolio_id: str, token: str | None = None) -> None:
        if self.backend_mode == "mock":
            _delete_mock_portfolio(portfolio_id)
            return

        self._delete(f"/portfolios/{portfolio_id}", token=token)

    def create_trade(
        self,
        portfolio_id: str,
        market_id: str,
        outcome: str,
        action: str,
        qty: float,
        price: float,
        token: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        side = str(action).strip().lower()
        if side not in {"buy", "sell"}:
            raise APIClientError("Action must be BUY or SELL")

        if self.backend_mode == "mock":
            return _create_mock_trade(
                portfolio_id=portfolio_id,
                market_id=market_id,
                outcome=outcome,
                side=side,
                quantity=qty,
                price=price,
                notes=notes,
            )

        payload: dict[str, Any] = {
            "market_id": market_id,
            "outcome": outcome,
            "side": side,
            "quantity": float(qty),
            "price": float(price),
        }
        if notes:
            payload["notes"] = notes

        return self._post_json(f"/portfolios/{portfolio_id}/trades", payload, token=token)

    def get_portfolio_metrics(self, portfolio_id: str, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            portfolio = _get_mock_portfolio(portfolio_id)
            trades = [t for t in _mock_trades() if str(t.get("portfolio_id")) == str(portfolio_id)]
            return {
                "portfolio_id": portfolio_id,
                "cash_balance": portfolio.get("cash_balance", 0.0),
                "trades_count": len(trades),
            }
        return self._get_json(f"/portfolios/{portfolio_id}/metrics", token=token)

    def get_portfolio_mtm(
        self,
        portfolio_id: str,
        *,
        token: str | None = None,
        resolution: int = 60,
    ) -> dict[str, Any]:
        if self.backend_mode == "mock":
            portfolio = _get_mock_portfolio(portfolio_id)
            current = float(portfolio.get("cash_balance", 0.0))
            initial = float(portfolio.get("initial_balance", current))
            return {
                "portfolio_id": portfolio_id,
                "current_value": current,
                "pnl": current - initial,
                "resolution": resolution,
            }
        return self._get_json(
            f"/portfolios/{portfolio_id}/mtm",
            token=token,
            params={"resolution": resolution},
        )

    # -------------------------
    # Market stream
    # -------------------------

    def start_stream(self, asset_ids: list[str], token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            asset_key = ",".join(sorted(str(asset_id) for asset_id in asset_ids))
            digest = hashlib.sha1(asset_key.encode("utf-8")).hexdigest()
            base_cent = int(digest[:2], 16)
            base_price = round(0.35 + (base_cent / 255.0) * 0.3, 4)
            bid_1 = round(max(0.01, base_price - 0.02), 4)
            bid_2 = round(max(0.01, base_price - 0.03), 4)
            ask_1 = round(min(0.99, base_price + 0.02), 4)
            ask_2 = round(min(0.99, base_price + 0.03), 4)
            st.session_state.market_stream_started = True
            st.session_state.orderbook = {
                "asset_ids": asset_ids,
                "bids": [[bid_1, 150], [bid_2, 220]],
                "asks": [[ask_1, 120], [ask_2, 210]],
            }
            st.session_state.orderbook_market_slug = asset_key or None
            return {"status": "started", "asset_ids": asset_ids}
        asset_id_path = ",".join(asset_ids)
        return self._post_json(f"/market-stream/start/{asset_id_path}", {}, token=token)

    def stop_stream(self, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            st.session_state.market_stream_started = False
            st.session_state.orderbook = {}
            st.session_state.orderbook_market_slug = None
            return {"status": "stopped"}
        return self._post_json("/market-stream/stop", {}, token=token)

    def get_orderbook(self, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            return dict(st.session_state.get("orderbook") or {})
        return self._get_json("/market-stream/orderbook", token=token)

    def get_latest_orderbook_change(self, token: str | None = None) -> dict[str, Any]:
        if self.backend_mode == "mock":
            return {
                "status": "mock",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return self._get_json("/market-stream/latest", token=token)


@lru_cache(maxsize=32)
def _load_fixture(name: str) -> Any:
    fixtures_dir = Path(__file__).resolve().parents[1] / "configs" / "fixtures"
    path = fixtures_dir / name
    if not path.exists():
        raise APIClientError(f"Missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _mock_portfolios() -> list[dict[str, Any]]:
    value = st.session_state.get("mock_portfolios")
    if value is None:
        return []
    return list(value)


def _set_mock_portfolios(portfolios: list[dict[str, Any]]) -> None:
    st.session_state.mock_portfolios = portfolios


def _mock_trades() -> list[dict[str, Any]]:
    value = st.session_state.get("mock_trades")
    if value is None:
        return []
    return list(value)


def _set_mock_trades(trades: list[dict[str, Any]]) -> None:
    st.session_state.mock_trades = trades


def _create_mock_portfolio(name: str, initial_balance: float) -> dict[str, Any]:
    portfolio = {
        "id": f"pf-{uuid4().hex[:8]}",
        "name": name.strip() or "Untitled",
        "initial_balance": float(initial_balance),
        "cash_balance": float(initial_balance),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    portfolios = _mock_portfolios()
    portfolios.append(portfolio)
    _set_mock_portfolios(portfolios)
    return portfolio


def _get_mock_portfolio(portfolio_id: str) -> dict[str, Any]:
    portfolios = _mock_portfolios()
    for portfolio in portfolios:
        if str(portfolio.get("id")) == str(portfolio_id):
            return portfolio
    raise APIClientError("Portfolio not found")


def _delete_mock_portfolio(portfolio_id: str) -> None:
    portfolios = _mock_portfolios()
    portfolios = [p for p in portfolios if str(p.get("id")) != str(portfolio_id)]
    _set_mock_portfolios(portfolios)

    trades = _mock_trades()
    trades = [t for t in trades if str(t.get("portfolio_id")) != str(portfolio_id)]
    _set_mock_trades(trades)


def _create_mock_trade(
    *,
    portfolio_id: str,
    market_id: str,
    outcome: str,
    side: str,
    quantity: float,
    price: float,
    notes: str | None,
) -> dict[str, Any]:
    if quantity <= 0:
        raise APIClientError("Quantity must be > 0")
    if not (0.0 <= price <= 1.0):
        raise APIClientError("Price must be between 0 and 1")

    portfolios = _mock_portfolios()
    portfolio = next((p for p in portfolios if str(p.get("id")) == str(portfolio_id)), None)
    if not portfolio:
        raise APIClientError("Unknown portfolio")

    cash = float(portfolio.get("cash_balance", 0.0))
    delta = float(quantity) * float(price)

    if side == "buy":
        if cash < delta:
            raise APIClientError("Insufficient cash")
        cash -= delta
    else:
        existing_trades = _mock_trades()
        if not can_sell(
            trades=existing_trades,
            portfolio_id=portfolio_id,
            market_id=market_id,
            outcome=outcome,
            qty=float(quantity),
        ):
            raise APIClientError("Insufficient position to sell")
        cash += delta

    portfolio["cash_balance"] = cash
    _set_mock_portfolios(portfolios)

    trade = {
        "id": f"tr-{uuid4().hex[:8]}",
        "portfolio_id": str(portfolio_id),
        "market_id": str(market_id),
        "outcome": str(outcome).upper(),
        "side": side,
        "quantity": float(quantity),
        "price": float(price),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }
    trades = _mock_trades()
    trades.append(trade)
    _set_mock_trades(trades)
    return trade
