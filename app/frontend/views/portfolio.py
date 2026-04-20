from __future__ import annotations

from collections import defaultdict

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


def _resolve_market(markets: list[dict], market_id: str) -> dict | None:
    needle = str(market_id)
    for market in markets:
        if str(market.get("slug") or "") == needle:
            return market
        if str(market.get("id") or "") == needle:
            return market
        if str(market.get("condition_id") or "") == needle:
            return market
    return None


def _build_position_rows(normalized_trades: list[dict], markets: list[dict]) -> list[dict]:
    # Keep position quantity and remaining cost basis in sync across BUY/SELL cycles.
    states: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"qty": 0.0, "cost": 0.0}
    )
    ordered = sorted(normalized_trades, key=lambda trade: str(trade.get("ts") or ""))

    for trade in ordered:
        market_id = str(trade.get("market_id") or "")
        outcome = str(trade.get("outcome") or "YES").upper()
        action = str(trade.get("action") or "BUY").upper()
        qty = float(trade.get("qty") or 0.0)
        price = float(trade.get("price") or 0.0)
        if qty <= 0:
            continue

        key = (market_id, outcome)
        state = states[key]

        if action == "BUY":
            state["qty"] += qty
            state["cost"] += qty * price
            continue

        # SELL: reduce inventory and cost basis proportionally to current average cost.
        available = max(0.0, float(state["qty"]))
        if available <= 0:
            continue
        sold = min(available, qty)
        avg_cost = (state["cost"] / state["qty"]) if state["qty"] > 0 else 0.0
        state["qty"] = max(0.0, available - sold)
        state["cost"] = max(0.0, float(state["cost"]) - (avg_cost * sold))

    rows: list[dict] = []
    for (market_id, outcome), state in states.items():
        qty = float(state["qty"])
        if qty <= 0:
            continue

        market = _resolve_market(markets, market_id)
        question = (
            (market or {}).get("question")
            or (market or {}).get("title")
            or market_id
        )
        outcomes = (market or {}).get("outcomes") or []
        prices = (market or {}).get("outcome_prices") or []

        avg_cost = (float(state["cost"]) / qty) if qty > 0 else 0.0
        current_price = avg_cost
        for index, current_outcome in enumerate(outcomes):
            if str(current_outcome).upper() == outcome and index < len(prices):
                try:
                    current_price = float(prices[index])
                except Exception:
                    current_price = avg_cost
                break

        current_value = qty * current_price
        pnl = current_value - float(state["cost"])
        pnl_pct = (pnl / float(state["cost"]) * 100.0) if float(state["cost"]) > 0 else 0.0

        rows.append(
            {
                "market_id": market_id,
                "market_slug": (market or {}).get("slug"),
                "market": question,
                "outcome": outcome,
                "qty": qty,
                "avg_entry": avg_cost,
                "current": current_price,
                "value": current_value,
                "cost": float(state["cost"]),
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }
        )

    rows.sort(key=lambda item: float(item.get("value") or 0.0), reverse=True)
    return rows


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
        markets = api.get_markets(token=token)
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

        display_positions = _build_position_rows(normalized_trades, markets)

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        render_section_header(
            "Positions",
            "Detailed open positions for the selected portfolio.",
        )
        if display_positions:
            df_positions = pd.DataFrame(
                [
                    {
                        "Market": row["market"],
                        "Outcome": row["outcome"],
                        "Qty": row["qty"],
                        "Avg entry": row["avg_entry"],
                        "Current": row["current"],
                        "Value": row["value"],
                        "PnL": row["pnl"],
                        "PnL %": row["pnl_pct"],
                    }
                    for row in display_positions
                ]
            )
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

            st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
            render_section_header(
                "Position actions",
                "Manage each open position quickly from this page.",
            )
            for row in display_positions:
                pnl_text = format_signed_currency(float(row["pnl"]))
                perf_text = f"{float(row['pnl_pct']):+.1f}%"
                st.markdown(
                    (
                        '<div class="info-card info-card--neutral">'
                        f"<strong>{row['market']} ({row['outcome']})</strong>"
                        f"<p>Qty: {float(row['qty']):.2f} | Avg: "
                        f"{format_currency(float(row['avg_entry']))} | Current: "
                        f"{format_currency(float(row['current']))} | PnL: {pnl_text} "
                        f"({perf_text})</p>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                col_open, col_liquidate = st.columns([1, 1])
                with col_open:
                    if st.button(
                        "Open market",
                        key=f"open_market_{selected}_{row['market_id']}_{row['outcome']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_portfolio_id = selected
                        st.session_state.nav_override = "Trading"
                        st.session_state.trading_view = "detail"
                        if row.get("market_slug"):
                            st.session_state.active_market_slug = row["market_slug"]
                        st.rerun()
                with col_liquidate:
                    if st.button(
                        "Liquidate",
                        key=f"liquidate_{selected}_{row['market_id']}_{row['outcome']}",
                        use_container_width=True,
                    ):
                        try:
                            api.create_trade(
                                portfolio_id=str(selected),
                                market_id=str(row["market_id"]),
                                outcome=str(row["outcome"]),
                                action="SELL",
                                qty=float(row["qty"]),
                                price=float(row["current"]),
                                token=token,
                                notes="Auto-liquidation from portfolio view",
                            )
                        except APIClientError as exc:
                            render_api_error_state(exc, resource="position liquidation")
                        else:
                            st.success("Position liquidated")
                            st.rerun()

            if normalized_trades:
                st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
                render_section_header(
                    "Recent trades",
                    "Latest executions for the selected portfolio.",
                )
                recent_df = (
                    pd.DataFrame(normalized_trades)
                    .sort_values(by="ts", ascending=False)
                    .head(12)
                )
                if not recent_df.empty:
                    recent_df = recent_df.rename(
                        columns={
                            "market_id": "Market ID",
                            "outcome": "Outcome",
                            "action": "Action",
                            "qty": "Qty",
                            "price": "Price",
                            "ts": "Timestamp",
                        }
                    )
                    recent_df["Qty"] = recent_df["Qty"].map(lambda value: f"{float(value):.2f}")
                    recent_df["Price"] = recent_df["Price"].map(format_currency)
                    st.dataframe(
                        dataframe_with_default_style(recent_df),
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
