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
        portfolios = api.list_portfolios(token=token)
    except APIClientError as exc:
        render_api_error_state(exc, resource="portfolio list")
        return

    all_trades: list[dict] = []
    portfolios_by_id: dict[str, dict] = {}
    for portfolio in portfolios:
        pid = str(portfolio.get("id") or portfolio.get("_id") or "")
        if not pid:
            continue
        portfolios_by_id[pid] = portfolio
        try:
            trades = api.get_trades(token=token, portfolio_id=pid, page=1, page_size=200)
        except APIClientError:
            continue
        for trade in trades:
            row = dict(trade)
            row["portfolio_name"] = portfolio.get("name", pid)
            all_trades.append(row)

    if not all_trades:
        render_empty_state(
            "There is no trade history yet.",
            (
                "Once you submit a paper trade, this page becomes the source "
                "of truth for your execution trail."
            ),
        )
        return

    selected_portfolio_id = str(st.session_state.get("selected_portfolio_id") or "")
    if selected_portfolio_id:
        all_trades = [
            t for t in all_trades if str(t.get("portfolio_id")) == selected_portfolio_id
        ]

    if not all_trades:
        render_empty_state(
            "This portfolio has no executions yet.",
            "Try another portfolio or place a first trade to populate the execution log.",
        )
        return

    df = pd.DataFrame(all_trades)
    if "side" not in df.columns and "action" in df.columns:
        df["side"] = df["action"]
    if "quantity" not in df.columns and "qty" in df.columns:
        df["quantity"] = df["qty"]
    if "created_at" not in df.columns and "ts" in df.columns:
        df["created_at"] = df["ts"]

    buy_count = (
        int((df["side"].astype(str).str.upper() == "BUY").sum())
        if "side" in df
        else 0
    )
    sell_count = (
        int((df["side"].astype(str).str.upper() == "SELL").sum())
        if "side" in df
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
    if "created_at" in display_df.columns:
        display_df["created_at"] = display_df["created_at"].map(format_timestamp)
    if "quantity" in display_df.columns:
        display_df["quantity"] = display_df["quantity"].map(format_quantity)
    if "price" in display_df.columns:
        display_df["price"] = display_df["price"].map(format_probability)
    display_df = display_df.rename(
        columns={
            "id": "Trade ID",
            "portfolio_name": "Portfolio",
            "portfolio_id": "Portfolio ID",
            "market_id": "Market ID",
            "outcome": "Outcome",
            "side": "Action",
            "quantity": "Qty",
            "price": "Price",
            "created_at": "Timestamp",
            "notes": "Note",
        }
    )
    st.dataframe(style_action_outcome_table(display_df), use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="trades.csv", mime="text/csv")
