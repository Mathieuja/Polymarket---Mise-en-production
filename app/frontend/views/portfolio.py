from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api_client import APIClient, APIClientError
from utils.portfolio_math import compute_portfolio_metrics
from utils.ui import (
    dataframe_with_default_style,
    format_currency,
    format_signed_currency,
    render_api_error_state,
    render_empty_state,
    render_kpi_row,
    render_page_header,
    render_section_header,
)


def render(api: APIClient) -> None:
    render_page_header(
        "Portfolio overview",
        (
            "Keep the portfolio experience simple: select a wallet, review "
            "its current value, then create a fresh one when you want a new "
            "simulation track."
        ),
        eyebrow="Portfolio",
        badge_label="Value tracking",
        badge_tone="brand",
    )

    token = st.session_state.get("token")
    try:
        markets = api.get_markets()
        portfolios = api.get_portfolios(token=token)
    except APIClientError as exc:
        render_api_error_state(exc, resource="portfolio data")
        return

    if portfolios:
        render_section_header(
            "Active portfolio",
            (
                "Choose the portfolio that should drive portfolio, metrics, "
                "and history views across the app."
            ),
        )
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
        try:
            trades = [t for t in api.get_trades(token=token) if t.get("portfolio_id") == selected]
        except APIClientError as exc:
            render_api_error_state(exc, resource="trade history")
            return
        metrics = compute_portfolio_metrics(
            portfolio=portfolio,
            trades=trades,
            markets=markets,
        )

        render_kpi_row(
            [
                {"label": "Cash", "value": format_currency(metrics.cash_usd)},
                {"label": "Positions value", "value": format_currency(metrics.positions_value_usd)},
                {"label": "Total value", "value": format_currency(metrics.total_value_usd)},
                {
                    "label": "PnL",
                    "value": format_currency(metrics.pnl_usd),
                    "delta": format_signed_currency(metrics.pnl_usd),
                    "tone": "success" if metrics.pnl_usd >= 0 else "danger",
                },
            ]
        )
    else:
        render_empty_state(
            "No portfolio has been created yet.",
            (
                "Create one below to start tracking paper trades, cash, and "
                "eventual portfolio performance."
            ),
        )

    render_section_header(
        "Create a portfolio",
        "Each portfolio can represent a different conviction set, strategy, or demo scenario.",
    )
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
        try:
            created = api.create_portfolio(
                name=name,
                initial_cash_usd=float(initial_cash),
                token=token,
            )
        except APIClientError as exc:
            render_api_error_state(exc, resource="portfolio creation")
            return
        st.session_state.selected_portfolio_id = created.get("id")
        st.success("Portfolio created")
        st.rerun()

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    render_section_header(
        "All portfolios",
        "A compact table to compare available portfolios and their current cash level.",
    )
    df = pd.DataFrame(portfolios)
    if not df.empty:
        if "cash_usd" in df.columns:
            df["cash_usd"] = df["cash_usd"].map(format_currency)
        if "initial_cash_usd" in df.columns:
            df["initial_cash_usd"] = df["initial_cash_usd"].map(format_currency)
        df = df.rename(
            columns={
                "id": "Portfolio ID",
                "name": "Name",
                "cash_usd": "Cash",
                "initial_cash_usd": "Initial cash",
            }
        )
        st.dataframe(dataframe_with_default_style(df), use_container_width=True, hide_index=True)
