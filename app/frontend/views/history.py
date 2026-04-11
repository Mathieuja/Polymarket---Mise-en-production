from __future__ import annotations

import pandas as pd
import streamlit as st

from app.frontend.utils.api_client import APIClient


def render(api: APIClient) -> None:
    st.header("History")

    token = st.session_state.get("token")
    trades = api.get_trades(token=token)

    if not trades:
        st.info("No trades yet (mock fixtures).")
        return

    selected_portfolio_id = st.session_state.get("selected_portfolio_id")
    if selected_portfolio_id:
        trades = [t for t in trades if t.get("portfolio_id") == selected_portfolio_id]

    df = pd.DataFrame(trades)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="trades.csv", mime="text/csv")
