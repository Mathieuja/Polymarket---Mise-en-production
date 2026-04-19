from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api_client import APIClient, APIClientError
from utils.ui import (
    format_probability,
    format_quantity,
    format_timestamp,
    render_api_error_state,
    render_empty_state,
    render_kpi_row,
    render_page_header,
    render_section_header,
    style_action_outcome_table,
)


def render(api: APIClient) -> None:
    render_page_header(
        "Trade history",
        (
            "Review the sequence of paper trades that built the current "
            "portfolio, then export the log for analysis or presentation."
        ),
        eyebrow="History",
        badge_label="Execution log",
        badge_tone="brand",
    )

    token = st.session_state.get("token")
    try:
        trades = api.get_trades(token=token)
    except APIClientError as exc:
        render_api_error_state(exc, resource="trade history")
        return

    if not trades:
        render_empty_state(
            "There is no trade history yet.",
            (
                "Once you submit a paper trade, this page becomes the source "
                "of truth for your execution trail."
            ),
        )
        return

    selected_portfolio_id = st.session_state.get("selected_portfolio_id")
    if selected_portfolio_id:
        trades = [t for t in trades if t.get("portfolio_id") == selected_portfolio_id]

    if not trades:
        render_empty_state(
            "This portfolio has no executions yet.",
            "Try another portfolio or place a first trade to populate the execution log.",
        )
        return

    df = pd.DataFrame(trades)
    buy_count = (
        int((df["action"].astype(str).str.upper() == "BUY").sum())
        if "action" in df
        else 0
    )
    sell_count = (
        int((df["action"].astype(str).str.upper() == "SELL").sum())
        if "action" in df
        else 0
    )
    render_kpi_row(
        [
            {"label": "Trades", "value": str(len(df))},
            {"label": "BUY orders", "value": str(buy_count)},
            {"label": "SELL orders", "value": str(sell_count)},
        ]
    )

    render_section_header(
        "Execution log",
        "A clean record of quantity, side, outcome, and timestamp for each trade.",
    )
    display_df = df.copy()
    if "ts" in display_df.columns:
        display_df["ts"] = display_df["ts"].map(format_timestamp)
    if "qty" in display_df.columns:
        display_df["qty"] = display_df["qty"].map(format_quantity)
    if "price" in display_df.columns:
        display_df["price"] = display_df["price"].map(format_probability)
    display_df = display_df.rename(
        columns={
            "id": "Trade ID",
            "portfolio_id": "Portfolio ID",
            "market_id": "Market ID",
            "outcome": "Outcome",
            "action": "Action",
            "qty": "Qty",
            "price": "Price",
            "ts": "Timestamp",
        }
    )
    st.dataframe(style_action_outcome_table(display_df), use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="trades.csv", mime="text/csv")
