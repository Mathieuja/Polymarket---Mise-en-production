from __future__ import annotations

import pandas as pd
import streamlit as st

from app.utils.api_client import APIClient
from app.utils.portfolio_math import compute_portfolio_metrics


def render(api: APIClient) -> None:
    st.header("Portfolio")

    token = st.session_state.get("token")
    markets = api.get_markets()
    portfolios = api.get_portfolios(token=token)

    st.subheader("Select portfolio")
    if portfolios:
        by_id = {p.get("id"): p for p in portfolios}

        def _format_portfolio_id(pid: str) -> str:
            p = by_id.get(pid, {})
            return f"{p.get('name')} ({pid})"

        ids = [p.get("id") for p in portfolios]
        current = st.session_state.get("selected_portfolio_id")
        if current not in ids:
            current = ids[0]

        selected = st.selectbox(
            "Portfolio",
            options=ids,
            index=ids.index(current),
            format_func=_format_portfolio_id,
        )
        st.session_state.selected_portfolio_id = selected

        portfolio = by_id[selected]
        trades = [t for t in api.get_trades(token=token) if t.get("portfolio_id") == selected]
        metrics = compute_portfolio_metrics(
            portfolio=portfolio,
            trades=trades,
            markets=markets,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cash", f"${metrics.cash_usd:,.2f}")
        c2.metric("Positions value", f"${metrics.positions_value_usd:,.2f}")
        c3.metric("Total value", f"${metrics.total_value_usd:,.2f}")
        c4.metric("PnL", f"${metrics.pnl_usd:,.2f}")
    else:
        st.info("No portfolios yet.")

    st.subheader("Create portfolio")
    with st.form("create_portfolio"):
        name = st.text_input("Name", value="My portfolio")
        initial_cash = st.number_input(
            "Initial cash (USD)",
            min_value=0.0,
            value=1000.0,
            step=50.0,
        )
        submitted = st.form_submit_button("Create", type="primary")

    if submitted:
        created = api.create_portfolio(name=name, initial_cash_usd=float(initial_cash), token=token)
        st.session_state.selected_portfolio_id = created.get("id")
        st.success("Portfolio created")
        st.rerun()

    st.subheader("All portfolios")
    df = pd.DataFrame(portfolios)
    st.dataframe(df, use_container_width=True, hide_index=True)
