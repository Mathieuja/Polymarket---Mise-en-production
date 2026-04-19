from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.api_client import APIClient, APIClientError
from utils.ui import (
    format_probability,
    format_quantity,
    render_api_error_state,
    render_empty_state,
    render_info_card,
    render_label_value_pairs,
    render_page_header,
    render_section_header,
)


def _build_price_chart(prices_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=prices_df["t"],
            y=prices_df["price"],
            mode="lines+markers",
            line={"color": "#1f6074", "width": 3},
            marker={"size": 7, "color": "#1f6074"},
            fill="tozeroy",
            fillcolor="rgba(31, 96, 116, 0.12)",
        )
    )
    fig.update_layout(
        margin={"l": 12, "r": 12, "t": 20, "b": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="YES price",
        yaxis={"tickformat": ".0%", "range": [0, 1], "gridcolor": "#d7e3eb"},
        xaxis={"gridcolor": "#edf3f7"},
        showlegend=False,
    )
    return fig


def render(api: APIClient) -> None:
    render_page_header(
        "Trading workspace",
        (
            "Read the current signal, compare YES and NO probabilities, then "
            "place a simulated trade with clean sizing and pricing controls."
        ),
        eyebrow="Market view",
        badge_label="Paper trading",
        badge_tone="brand",
    )

    token = st.session_state.get("token")
    try:
        markets = api.get_markets()
        portfolios = api.get_portfolios(token=token)
    except APIClientError as exc:
        render_api_error_state(exc, resource="market and portfolio data")
        return

    if not markets:
        render_empty_state(
            "No markets are available right now.",
            (
                "Load fixture data or connect the API mode so the trading "
                "workspace can surface active prediction markets."
            ),
        )
        return

    if not portfolios:
        render_empty_state(
            "Create a portfolio before placing your first trade.",
            (
                "The trading ticket needs a target portfolio so it can track "
                "cash, exposure, and future performance."
            ),
        )
        return

    selected_portfolio_id = st.session_state.get("selected_portfolio_id")
    portfolio_ids = [p.get("id") for p in portfolios]
    if selected_portfolio_id not in portfolio_ids:
        selected_portfolio_id = portfolio_ids[0]
        st.session_state.selected_portfolio_id = selected_portfolio_id

    market_by_id = {str(m.get("id")): m for m in markets}
    market_ids = list(market_by_id)
    selected_market_id = st.session_state.get("selected_market_id")
    if selected_market_id not in market_ids:
        selected_market_id = market_ids[0]
        st.session_state.selected_market_id = selected_market_id

    top_left, top_right = st.columns([0.78, 1.22], gap="large")

    with top_left:
        render_section_header(
            "Market selection",
            "Choose the contract and portfolio you want to use for this simulation.",
        )
        portfolio_label_map = {
            str(p.get("id")): f"{p.get('name')} ({p.get('id')})" for p in portfolios
        }
        selected_portfolio_id = st.selectbox(
            "Portfolio",
            options=portfolio_ids,
            index=portfolio_ids.index(selected_portfolio_id),
            format_func=lambda item: portfolio_label_map.get(str(item), str(item)),
        )
        st.session_state.selected_portfolio_id = selected_portfolio_id

        selected_market_id = st.selectbox(
            "Market",
            options=market_ids,
            index=market_ids.index(selected_market_id),
            format_func=lambda item: market_by_id[str(item)].get("title", str(item)),
        )
        st.session_state.selected_market_id = selected_market_id

        market = market_by_id[str(selected_market_id)]
        latest_yes_price = 0.5
        if isinstance(market.get("prices"), list) and market["prices"]:
            latest_yes_price = float(market["prices"][-1].get("price", 0.5))

        render_info_card(
            "How to read this screen",
            (
                "The YES price can be read as the market-implied probability "
                "of the event. Use the NO side when you want the complementary view."
            ),
            tone="brand",
        )

    with top_right:
        latest_no_price = 1.0 - latest_yes_price
        st.markdown(
            f"""
            <section class="market-summary">
              <div class="market-summary__title">{market.get('title')}</div>
              <p>
                The market card highlights the current probability split and a short
                recent price history so you can place a trade with context.
              </p>
              <div class="split-pills">
                <div class="split-pill split-pill--yes">
                  <div class="split-pill__label">YES</div>
                  <div class="split-pill__value">{format_probability(latest_yes_price)}</div>
                </div>
                <div class="split-pill split-pill--no">
                  <div class="split-pill__label">NO</div>
                  <div class="split-pill__value">{format_probability(latest_no_price)}</div>
                </div>
              </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        render_label_value_pairs(
            [
                ("Market ID", str(market.get("id"))),
                ("Latest YES price", format_probability(latest_yes_price)),
                ("Latest NO price", format_probability(latest_no_price)),
                ("Data points", str(len(market.get("prices", [])))),
            ]
        )

    prices = market.get("prices")
    if isinstance(prices, list) and prices:
        prices_df = pd.DataFrame(prices)
        if {"t", "price"}.issubset(prices_df.columns):
            render_section_header(
                "Price signal",
                "A compact view of how the YES probability moved over the latest observed points.",
            )
            st.plotly_chart(
                _build_price_chart(prices_df),
                use_container_width=True,
                config={"displayModeBar": False},
            )

    render_section_header(
        "Trade ticket",
        "Keep the workflow simple: pick side, action, quantity, and execution price.",
    )
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
    st.caption(
        "Ticket preview: "
        f"{action} {format_quantity(qty)} contract(s) on {outcome} "
        f"at {format_probability(price)}."
    )
    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

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
            if isinstance(exc, APIClientError):
                render_api_error_state(exc, resource="trade creation")
            else:
                st.error(str(exc))
            return

        st.success("Trade submitted")
        st.rerun()
