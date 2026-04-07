from __future__ import annotations

import pandas as pd
import streamlit as st

from app.utils.api_client import APIClient


def render(api: APIClient) -> None:
    st.header("History")

    token = st.session_state.get("token")
    portfolios = api.get_portfolios(token=token)
    if not portfolios:
        st.info("Create a portfolio first (Portfolio page).")
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

    st.caption(f"Showing history for portfolio: `{selected_portfolio_name}` (`{selected_portfolio_id}`)")

    trades = api.get_trades(token=token)

    if not trades:
        st.info("No trades yet (mock fixtures).")
        return

    if selected_portfolio_id:
        trades = [t for t in trades if t.get("portfolio_id") == selected_portfolio_id]

    df = pd.DataFrame(trades)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="trades.csv", mime="text/csv")
