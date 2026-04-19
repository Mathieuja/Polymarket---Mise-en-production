from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.api_client import APIClient, APIClientError
from utils.portfolio_math import (
    compute_portfolio_metrics,
    compute_positions,
    market_outcome_price_usd,
)
from utils.ui import (
    dataframe_with_default_style,
    format_currency,
    format_probability,
    format_signed_currency,
    render_api_error_state,
    render_empty_state,
    render_kpi_row,
    render_page_header,
    render_section_header,
)


def render(api: APIClient) -> None:
    render_page_header(
        "Performance metrics",
        (
            "This screen translates trades into portfolio value: cash left, "
            "mark-to-market exposure, and PnL in one place."
        ),
        eyebrow="Metrics",
        badge_label="Portfolio analytics",
        badge_tone="brand",
    )
    token = st.session_state.get("token")

    try:
        markets = api.get_markets()
        portfolios = api.get_portfolios(token=token)
    except APIClientError as exc:
        render_api_error_state(exc, resource="metrics inputs")
        return

    if not portfolios:
        render_empty_state(
            "Metrics appear after you create a portfolio.",
            (
                "Once a portfolio exists, this page can summarize value, "
                "exposure, and current mark-to-market performance."
            ),
        )
        return

    selected_portfolio_id = st.session_state.get("selected_portfolio_id")
    by_id = {p.get("id"): p for p in portfolios}
    if selected_portfolio_id not in by_id:
        selected_portfolio_id = portfolios[0].get("id")
        st.session_state.selected_portfolio_id = selected_portfolio_id

    portfolio = by_id[selected_portfolio_id]
    try:
        trades = [
            t for t in api.get_trades(token=token) if t.get("portfolio_id") == selected_portfolio_id
        ]
    except APIClientError as exc:
        render_api_error_state(exc, resource="trade history")
        return

    metrics = compute_portfolio_metrics(portfolio=portfolio, trades=trades, markets=markets)
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

    if not trades:
        render_empty_state(
            "This portfolio has no trades yet.",
            (
                "Place a first paper trade in the trading workspace and this "
                "page will begin surfacing live-looking metrics."
            ),
        )
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
    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    render_section_header(
        "Open positions",
        "Current marked positions by market and side, based on the latest available mock price.",
    )
    if not df.empty:
        display_df = df.copy()
        display_df["price"] = display_df["price"].map(format_probability)
        display_df["qty"] = display_df["qty"].map(lambda value: f"{float(value):.2f}")
        display_df["value"] = display_df["value"].map(format_currency)
        display_df = display_df.rename(
            columns={
                "market_id": "Market ID",
                "market": "Market",
                "outcome": "Outcome",
                "qty": "Qty",
                "price": "Current price",
                "value": "Marked value",
            }
        )
        st.dataframe(
            dataframe_with_default_style(display_df),
            use_container_width=True,
            hide_index=True,
        )

        chart_df = df.sort_values("value", ascending=True)
        fig = px.bar(
            chart_df,
            x="value",
            y="market",
            orientation="h",
            color="outcome",
            color_discrete_map={"YES": "#1f6074", "NO": "#d18a4d"},
        )
        fig.update_layout(
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Marked value",
            yaxis_title="",
            legend_title="Outcome",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
