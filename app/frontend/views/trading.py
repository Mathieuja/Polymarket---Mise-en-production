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


def _normalize_market(market: dict) -> dict:
    slug = market.get("slug") or market.get("id") or market.get("condition_id")
    title = market.get("question") or market.get("title") or str(slug)
    outcomes = market.get("outcomes") or ["YES", "NO"]
    prices = market.get("outcome_prices") or []
    yes_price = 0.5
    no_price = 0.5
    if isinstance(outcomes, list) and isinstance(prices, list):
        for index, outcome in enumerate(outcomes):
            if index >= len(prices):
                continue
            try:
                value = float(prices[index])
            except Exception:
                continue
            if str(outcome).upper() == "YES":
                yes_price = value
            if str(outcome).upper() == "NO":
                no_price = value
    if no_price == 0.5 and yes_price != 0.5:
        no_price = 1.0 - yes_price

    return {
        **market,
        "slug": str(slug),
        "title": title,
        "yes_price": yes_price,
        "no_price": no_price,
        "volume_24h": float(market.get("volume_24h", market.get("volume", 0.0)) or 0.0),
        "liquidity": float(market.get("liquidity", 0.0) or 0.0),
    }


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


def _render_market_list(api: APIClient, portfolios: list[dict], token: str | None) -> None:
    render_section_header(
        "Market directory",
        "Browse active contracts, inspect probabilities, then open a detailed trade ticket.",
    )

    col_search, col_sort = st.columns([1.7, 1.0])
    search = col_search.text_input("Search", value=st.session_state.get("trading_search", ""))
    sort_label = col_sort.selectbox(
        "Sort by",
        options=["Volume (desc)", "Newest"],
        index=0,
    )
    st.session_state.trading_search = search

    page = int(st.session_state.get("trading_page", 1))
    page_size = 12

    try:
        listing = api.list_markets(
            page=page,
            page_size=page_size,
            search=search or None,
            active=True,
            sort_by="volume_24h_desc" if "Volume" in sort_label else "created_at_desc",
        )
        markets = [_normalize_market(m) for m in listing.get("items", [])]
        total_pages = int(listing.get("total_pages", 1) or 1)
    except APIClientError:
        markets = [_normalize_market(m) for m in api.get_markets()]
        if search:
            search_l = search.lower()
            markets = [m for m in markets if search_l in str(m.get("title", "")).lower()]
        if "Volume" in sort_label:
            markets = sorted(markets, key=lambda m: m.get("volume_24h", 0.0), reverse=True)
        total_pages = 1

    if not markets:
        render_empty_state(
            "No matching markets found.",
            "Change the search criteria or refresh market synchronization.",
        )
        return

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    for market in markets:
        with st.container(border=True):
            st.markdown(f"### {market['title']}")
            cols = st.columns([1.1, 1.1, 1.2, 0.8])
            cols[0].metric("YES", format_probability(float(market["yes_price"])))
            cols[1].metric("NO", format_probability(float(market["no_price"])))
            cols[2].metric("24h volume", format_quantity(float(market["volume_24h"])))
            if cols[3].button(
                "Open",
                key=f"open_market_{market['slug']}",
                use_container_width=True,
            ):
                st.session_state.active_market_slug = market["slug"]
                st.session_state.trading_view = "detail"
                st.rerun()

    col_prev, col_page, col_next = st.columns([0.8, 1.0, 0.8])
    with col_prev:
        if st.button("Previous", disabled=page <= 1, use_container_width=True):
            st.session_state.trading_page = page - 1
            st.rerun()
    with col_page:
        st.caption(f"Page {page} / {total_pages}")
    with col_next:
        if st.button("Next", disabled=page >= total_pages, use_container_width=True):
            st.session_state.trading_page = page + 1
            st.rerun()


def _load_market_detail(api: APIClient, slug: str) -> dict | None:
    try:
        market = api.get_market(slug)
        return _normalize_market(market)
    except APIClientError:
        pass
    for market in api.get_markets():
        normalized = _normalize_market(market)
        if str(normalized.get("slug")) == str(slug):
            return normalized
    return None


def _render_market_detail(api: APIClient, portfolios: list[dict], token: str | None) -> None:
    slug = st.session_state.get("active_market_slug")
    if not slug:
        st.session_state.trading_view = "list"
        st.rerun()

    market = _load_market_detail(api, slug)
    if not market:
        render_empty_state("Market not found.", "Return to list view and select another market.")
        if st.button("Back to markets"):
            st.session_state.trading_view = "list"
            st.session_state.active_market_slug = None
            st.rerun()
        return

    top_left, top_right = st.columns([1.4, 1.0], gap="large")
    with top_left:
        if st.button("Back to markets"):
            st.session_state.trading_view = "list"
            st.rerun()
        st.markdown(f"## {market['title']}")
        render_label_value_pairs(
            [
                ("Slug", str(market.get("slug"))),
                ("Condition ID", str(market.get("condition_id") or "-")),
                ("24h volume", format_quantity(float(market.get("volume_24h", 0.0)))),
                ("Liquidity", format_quantity(float(market.get("liquidity", 0.0)))),
            ]
        )
    with top_right:
        st.markdown(
            f"""
            <section class="market-summary">
              <div class="market-summary__title">Current split</div>
              <div class="split-pills">
                <div class="split-pill split-pill--yes">
                  <div class="split-pill__label">YES</div>
                                    <div class="split-pill__value">
                                        {format_probability(float(market['yes_price']))}
                                    </div>
                </div>
                <div class="split-pill split-pill--no">
                  <div class="split-pill__label">NO</div>
                                    <div class="split-pill__value">
                                        {format_probability(float(market['no_price']))}
                                    </div>
                </div>
              </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    history_df = None
    try:
        history = api.get_price_history(str(market["slug"]), outcome_index=0)
        prices = history.get("points") if isinstance(history, dict) else history
        if isinstance(prices, list) and prices:
            history_df = pd.DataFrame(prices)
            if "timestamp" in history_df.columns and "price" in history_df.columns:
                history_df = history_df.rename(columns={"timestamp": "t"})
    except APIClientError:
        history_df = None

    if history_df is None:
        fallback_prices = market.get("prices")
        if isinstance(fallback_prices, list) and fallback_prices:
            history_df = pd.DataFrame(fallback_prices)

    if history_df is not None and {"t", "price"}.issubset(history_df.columns):
        render_section_header("Price signal", "Recent evolution of YES implied probability.")
        st.plotly_chart(
            _build_price_chart(history_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    render_section_header(
        "Trade ticket",
        "Choose target portfolio, side, and execution settings before submitting the paper order.",
    )
    portfolio_ids = [str(p.get("id") or p.get("_id")) for p in portfolios]
    selected_portfolio_id = str(st.session_state.get("selected_portfolio_id") or portfolio_ids[0])
    if selected_portfolio_id not in portfolio_ids:
        selected_portfolio_id = portfolio_ids[0]
    st.session_state.selected_portfolio_id = selected_portfolio_id

    col_portfolio, col_side, col_action = st.columns([1.2, 0.9, 0.9])
    selected_portfolio_id = col_portfolio.selectbox(
        "Portfolio",
        options=portfolio_ids,
        index=portfolio_ids.index(selected_portfolio_id),
        format_func=lambda pid: next(
            (
                f"{p.get('name', pid)} ({pid})"
                for p in portfolios
                if str(p.get("id") or p.get("_id")) == str(pid)
            ),
            str(pid),
        ),
    )
    st.session_state.selected_portfolio_id = selected_portfolio_id

    outcomes = [str(o).upper() for o in market.get("outcomes", ["YES", "NO"]) if str(o).upper()]
    if not outcomes:
        outcomes = ["YES", "NO"]
    outcome = col_side.selectbox("Outcome", options=outcomes, index=0)
    action = col_action.selectbox("Action", options=["BUY", "SELL"], index=0)

    default_price = float(market["yes_price"])
    if outcome == "NO":
        default_price = float(market["no_price"])
    qty = st.number_input("Quantity", min_value=1.0, value=1.0, step=1.0)
    price = st.slider("Price", min_value=0.0, max_value=1.0, value=default_price, step=0.01)
    note = st.text_input("Note (optional)", value="")
    st.caption(
        f"Preview: {action} {format_quantity(qty)} {outcome} at {format_probability(price)}"
    )

    if st.button("Submit trade", type="primary"):
        market_id = str(market.get("id") or market.get("slug"))
        try:
            api.create_trade(
                portfolio_id=selected_portfolio_id,
                market_id=market_id,
                outcome=outcome,
                action=action,
                qty=float(qty),
                price=float(price),
                token=token,
                notes=note or None,
            )
        except APIClientError as exc:
            render_api_error_state(exc, resource="trade creation")
            return
        st.success("Trade submitted")
        st.rerun()

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    render_section_header(
        "Order book",
        "Live order book snapshot when stream endpoint is available.",
    )
    try:
        orderbook = api.get_orderbook(token=token)
        st.session_state.orderbook = orderbook
    except APIClientError:
        orderbook = st.session_state.get("orderbook")

    if isinstance(orderbook, dict) and orderbook:
        st.json(orderbook)
    else:
        render_info_card(
            "Order book unavailable",
            "Start market stream from backend to display real-time order book updates.",
            tone="warning",
        )


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
        portfolios = api.list_portfolios(token=token)
    except APIClientError as exc:
        render_api_error_state(exc, resource="portfolio data")
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

    if st.session_state.get("trading_view") == "detail":
        _render_market_detail(api, portfolios, token)
    else:
        _render_market_list(api, portfolios, token)
