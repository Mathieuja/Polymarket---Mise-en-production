from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


def init_session_state() -> None:
    defaults: dict[str, object] = {
        "is_authenticated": False,
        "token": None,
        "user_email": None,
        "user": None,
        "nav_page": "Login",
        "nav_override": None,
        "nav_key": 0,
        "selected_market_id": None,
        "selected_portfolio_id": None,
        "metrics_portfolio_id": None,
        "trading_view": "list",
        "trading_page": 1,
        "mock_portfolios": None,
        "mock_trades": None,
        "orderbook": None,
        "market_stream_started": False,
        "active_market_slug": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    _init_mock_data_if_needed()


def _init_mock_data_if_needed() -> None:
    if st.session_state.get("mock_portfolios") is None:
        st.session_state.mock_portfolios = _read_fixture_json("portfolios.json")
        for p in st.session_state.mock_portfolios:
            p.setdefault("initial_cash_usd", float(p.get("cash_usd", 0.0)))

    if st.session_state.get("mock_trades") is None:
        st.session_state.mock_trades = _read_fixture_json("trades.json")

    if st.session_state.get("selected_portfolio_id") is None and st.session_state.mock_portfolios:
        st.session_state.selected_portfolio_id = st.session_state.mock_portfolios[0].get("id")


def _read_fixture_json(filename: str):
    fixtures_dir = Path(__file__).resolve().parents[1] / "configs" / "fixtures"
    path = fixtures_dir / filename
    return json.loads(path.read_text(encoding="utf-8"))


def logout() -> None:
    st.session_state.is_authenticated = False
    st.session_state.token = None
    st.session_state.user_email = None
    st.session_state.user = None
    st.session_state.nav_page = "Login"
    st.session_state.nav_override = None
    st.session_state.trading_view = "list"
    st.session_state.active_market_slug = None
