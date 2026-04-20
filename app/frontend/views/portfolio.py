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
        portfolios = api.list_portfolios(token=token)
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
        by_id = {str(p.get("id") or p.get("_id")): p for p in portfolios}

        def _format_portfolio_id(pid: str) -> str:
            p = by_id.get(pid, {})
            return f"{p.get('name')} ({pid})"

        ids = [str(p.get("id") or p.get("_id")) for p in portfolios]
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
            trades = api.get_trades(token=token, portfolio_id=selected, page=1, page_size=200)
        except APIClientError as exc:
            render_api_error_state(exc, resource="trade history")
            return

        # Normalize mock/backend portfolio shape.
        if "cash_usd" not in portfolio:
            portfolio["cash_usd"] = float(
                portfolio.get("cash_balance", portfolio.get("initial_balance", 0.0))
            )
        if "initial_cash_usd" not in portfolio:
            portfolio["initial_cash_usd"] = float(
                portfolio.get("initial_balance", portfolio.get("cash_usd", 0.0))
            )

        normalized_trades: list[dict] = []
        for trade in trades:
            normalized_trades.append(
                {
                    "portfolio_id": str(trade.get("portfolio_id")),
                    "market_id": str(trade.get("market_id")),
                    "outcome": str(trade.get("outcome", "YES")).upper(),
                    "action": str(trade.get("side", trade.get("action", "BUY"))).upper(),
                    "qty": float(trade.get("quantity", trade.get("qty", 0.0))),
                    "price": float(trade.get("price", 0.0)),
                    "ts": trade.get("created_at", trade.get("ts")),
                }
            )

        metrics = compute_portfolio_metrics(
            portfolio=portfolio,
            trades=normalized_trades,
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

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        col_metrics, col_trade, col_delete = st.columns([1, 1, 1])
        with col_metrics:
            if st.button("View metrics", key=f"pf_metrics_{selected}", use_container_width=True):
                st.session_state.metrics_portfolio_id = selected
                st.session_state.nav_override = "Metrics"
                st.rerun()
        with col_trade:
            if st.button("Open trading", key=f"pf_trade_{selected}", use_container_width=True):
                st.session_state.selected_portfolio_id = selected
                st.session_state.nav_override = "Trading"
                st.rerun()
        with col_delete:
            if st.button("Delete portfolio", key=f"pf_delete_{selected}", use_container_width=True):
                try:
                    api.delete_portfolio(selected, token=token)
                except APIClientError as exc:
                    st.error(str(exc))
                else:
                    st.success("Portfolio deleted")
                    st.session_state.selected_portfolio_id = None
                    st.rerun()

        position_rows: list[dict] = []
        for trade in normalized_trades:
            market_id = trade["market_id"]
            outcome = trade["outcome"]
            key = (market_id, outcome)
            existing = next((r for r in position_rows if r["key"] == key), None)
            signed_qty = trade["qty"] if trade["action"] == "BUY" else -trade["qty"]
            if existing is None:
                position_rows.append(
                    {
                        "key": key,
                        "market_id": market_id,
                        "outcome": outcome,
                        "qty": signed_qty,
                        "cost": trade["qty"] * trade["price"] if trade["action"] == "BUY" else 0.0,
                    }
                )
            else:
                if trade["action"] == "BUY":
                    existing["cost"] += trade["qty"] * trade["price"]
                existing["qty"] += signed_qty

        display_positions: list[dict] = []
        markets_by_slug = {str(m.get("slug") or m.get("id")): m for m in markets}
        for row in position_rows:
            if row["qty"] <= 0:
                continue
            market = markets_by_slug.get(str(row["market_id"]))
            question = (
                (market or {}).get("question")
                or (market or {}).get("title")
                or row["market_id"]
            )
            outcomes = (market or {}).get("outcomes") or []
            prices = (market or {}).get("outcome_prices") or []
            current_price = None
            for index, outcome in enumerate(outcomes):
                if str(outcome).upper() == row["outcome"] and index < len(prices):
                    try:
                        current_price = float(prices[index])
                    except Exception:
                        current_price = None
                    break
            avg_cost = (row["cost"] / row["qty"]) if row["qty"] > 0 else 0.0
            if current_price is None:
                current_price = avg_cost
            current_value = row["qty"] * current_price
            pnl = current_value - row["cost"]
            pnl_pct = (pnl / row["cost"] * 100.0) if row["cost"] > 0 else 0.0
            display_positions.append(
                {
                    "Market": question,
                    "Outcome": row["outcome"],
                    "Qty": row["qty"],
                    "Avg entry": avg_cost,
                    "Current": current_price,
                    "Value": current_value,
                    "PnL": pnl,
                    "PnL %": pnl_pct,
                }
            )

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        render_section_header(
            "Positions",
            "Detailed open positions for the selected portfolio.",
        )
        if display_positions:
            df_positions = pd.DataFrame(display_positions)
            df_positions["Qty"] = df_positions["Qty"].map(lambda value: f"{float(value):.2f}")
            df_positions["Avg entry"] = df_positions["Avg entry"].map(format_currency)
            df_positions["Current"] = df_positions["Current"].map(format_currency)
            df_positions["Value"] = df_positions["Value"].map(format_currency)
            df_positions["PnL"] = df_positions["PnL"].map(format_signed_currency)
            df_positions["PnL %"] = df_positions["PnL %"].map(lambda value: f"{value:+.1f}%")
            st.dataframe(
                dataframe_with_default_style(df_positions),
                use_container_width=True,
                hide_index=True,
            )
        else:
            render_empty_state(
                "No open positions.",
                "Submit a trade in the Trading view to populate this section.",
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
