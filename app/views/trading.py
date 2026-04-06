from __future__ import annotations

import pandas as pd
import streamlit as st

from app.utils.api_client import APIClient


def render(api: APIClient) -> None:
    st.header("Trading")

    token = st.session_state.get("token")
    markets = api.get_markets()
    if not markets:
        st.warning("No markets available (check fixtures)")
        return

    portfolios = api.get_portfolios(token=token)
    if not portfolios:
        st.info("Create a portfolio first (Portfolio page).")
        return

    selected_portfolio_id = st.session_state.get("selected_portfolio_id")
    portfolio_ids = [p.get("id") for p in portfolios]
    if selected_portfolio_id not in portfolio_ids:
        selected_portfolio_id = portfolio_ids[0]
        st.session_state.selected_portfolio_id = selected_portfolio_id

    df = pd.DataFrame(markets)
    label_col = "title" if "title" in df.columns else df.columns[0]

    choice = st.selectbox("Market", options=df[label_col].tolist())
    market = next((m for m in markets if m.get(label_col) == choice), markets[0])

    st.subheader("Market details")
    st.json(market)

    if "prices" in market and isinstance(market["prices"], list):
        prices_df = pd.DataFrame(market["prices"])
        if {"t", "price"}.issubset(prices_df.columns):
            st.line_chart(prices_df.set_index("t")["price"])

    st.subheader("Place trade (mock)")
    col1, col2, col3 = st.columns(3)
    outcome = col1.selectbox("Outcome", options=["YES", "NO"], index=0)
    action = col2.selectbox("Action", options=["BUY", "SELL"], index=0)
    qty = col3.number_input("Quantity", min_value=1.0, value=1.0, step=1.0)

    default_price = 0.5
    if isinstance(market.get("prices"), list) and market["prices"]:
        default_price = float(market["prices"][-1].get("price", 0.5))
        if outcome == "NO":
            default_price = 1.0 - default_price

    price = st.slider("Price", min_value=0.0, max_value=1.0, value=float(default_price), step=0.01)

    if st.button("Submit trade", type="primary"):
        try:
            api.create_trade(
                portfolio_id=str(selected_portfolio_id),
                market_id=str(market.get("id")),
                outcome=outcome,
                action=action,
                qty=float(qty),
                price=float(price),
                token=token,
            )
        except Exception as exc:
            st.error(str(exc))
            return

        st.success("Trade submitted")
        st.rerun()
