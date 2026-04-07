from __future__ import annotations

import pandas as pd
import streamlit as st

from app.utils.api_client import APIClient
from app.utils.portfolio_math import (
    compute_portfolio_metrics,
    compute_positions,
    market_outcome_price_usd,
)


def render(api: APIClient) -> None:
    st.header("Metrics")
    token = st.session_state.get("token")

    markets = api.get_markets()
    portfolios = api.get_portfolios(token=token)
    if not portfolios:
        st.info("Create a portfolio first.")
        return

    portfolio_map = {p.get("name"): p.get("id") for p in portfolios}
    portfolio_names = list(portfolio_map.keys())

    # --- Portfolio selection ---
    selected_portfolio_name = st.selectbox(
        "Select Portfolio",
        options=portfolio_names,
        index=0,
    )
    selected_portfolio_id = portfolio_map.get(selected_portfolio_name)
    st.session_state.selected_portfolio_id = selected_portfolio_id
    # ---

    st.caption(f"Showing metrics for portfolio: `{selected_portfolio_name}` (`{selected_portfolio_id}`)")

    by_id = {p.get("id"): p for p in portfolios}
    portfolio = by_id[selected_portfolio_id]
    trades = [
        t for t in api.get_trades(token=token) if t.get("portfolio_id") == selected_portfolio_id
    ]

    metrics = compute_portfolio_metrics(portfolio=portfolio, trades=trades, markets=markets)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"${metrics.cash_usd:,.2f}")
    c2.metric("Positions value", f"${metrics.positions_value_usd:,.2f}")
    c3.metric("Total value", f"${metrics.total_value_usd:,.2f}")
    c4.metric("PnL", f"${metrics.pnl_usd:,.2f}")

    if not trades:
        st.info("No trades for this portfolio yet.")
        return

    positions = compute_positions(trades)
    market_by_id = {str(m.get("id")): m for m in markets}

    rows: list[dict[str, object]] = []
    for (pf_id, mkt_id, outcome), qty in positions.items():
        if pf_id != str(selected_portfolio_id):
            continue
        market = market_by_id.get(mkt_id)
        if not market:
            continue
        price = market_outcome_price_usd(market, outcome)
        rows.append(
            {
                "market_id": mkt_id,
                "market": market.get("title"),
                "outcome": outcome,
                "qty": qty,
                "price": price,
                "value": qty * price,
            }
        )

    df = pd.DataFrame(rows)
    st.subheader("Positions")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.bar_chart(df.set_index("market")[["value"]])
