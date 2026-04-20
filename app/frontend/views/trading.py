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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_levels(levels: object, *, reverse: bool) -> list[tuple[float, float]]:
    parsed: list[tuple[float, float]] = []
    if isinstance(levels, dict):
        for price, qty in levels.items():
            p = _to_float(price, -1.0)
            q = _to_float(qty, 0.0)
            if p >= 0 and q > 0:
                parsed.append((p, q))
    elif isinstance(levels, list):
        for row in levels:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                p = _to_float(row[0], -1.0)
                q = _to_float(row[1], 0.0)
            elif isinstance(row, dict):
                p = _to_float(row.get("price", row.get("p")), -1.0)
                q = _to_float(row.get("size", row.get("qty", row.get("quantity"))), 0.0)
            else:
                continue
            if p >= 0 and q > 0:
                parsed.append((p, q))

    parsed.sort(key=lambda item: item[0], reverse=reverse)
    return parsed


def _extract_orderbook_payload(raw_orderbook: object) -> dict:
    if not isinstance(raw_orderbook, dict):
        return {}

    messages = raw_orderbook.get("messages")
    if isinstance(messages, dict):
        return messages

    data = raw_orderbook.get("data")
    if isinstance(data, dict) and isinstance(data.get("messages"), dict):
        return data["messages"]

    return raw_orderbook


def _book_with_levels(entry: object) -> dict[str, list[tuple[float, float]]] | None:
    if not isinstance(entry, dict):
        return None
    if "bids" not in entry and "asks" not in entry:
        return None
    return {
        "bids": _normalize_levels(entry.get("bids", {}), reverse=True),
        "asks": _normalize_levels(entry.get("asks", {}), reverse=False),
    }


def _map_orderbook_by_outcome(raw_orderbook: object, market: dict) -> dict[str, dict]:
    payload = _extract_orderbook_payload(raw_orderbook)
    outcomes = [
        str(outcome).upper()
        for outcome in market.get("outcomes", ["YES", "NO"])
        if str(outcome).strip()
    ]
    if not outcomes:
        outcomes = ["YES", "NO"]

    token_ids = [str(token_id) for token_id in market.get("clob_token_ids", []) if token_id]

    mapped: dict[str, dict] = {}

    # Case 1: direct payload is a single orderbook with bids/asks.
    direct = _book_with_levels(payload)
    if direct is not None:
        for outcome in outcomes:
            mapped[outcome] = direct
        return mapped

    # Case 2: payload is token keyed.
    first_detected: dict | None = None
    for idx, outcome in enumerate(outcomes):
        candidates: list[str] = [outcome, outcome.lower()]
        if idx < len(token_ids):
            candidates.insert(0, token_ids[idx])

        selected: dict | None = None
        for candidate in candidates:
            candidate_entry = _book_with_levels(payload.get(candidate))
            if candidate_entry is not None:
                selected = candidate_entry
                break

        if selected is None:
            # Fallback: first orderbook-looking entry.
            for value in payload.values():
                maybe_entry = _book_with_levels(value)
                if maybe_entry is not None:
                    selected = maybe_entry
                    break

        if selected is not None:
            mapped[outcome] = selected
            if first_detected is None:
                first_detected = selected

    if first_detected is not None:
        for outcome in outcomes:
            mapped.setdefault(outcome, first_detected)

    return mapped


def _estimate_executions(
    levels: list[tuple[float, float]],
    quantity: float,
) -> tuple[list[tuple[float, float]], float, float, float | None]:
    remaining = float(quantity)
    executions: list[tuple[float, float]] = []

    for price, available in levels:
        if remaining <= 0:
            break
        take = min(remaining, available)
        if take <= 0:
            continue
        executions.append((take, price))
        remaining -= take

    total = sum(qty * price for qty, price in executions)
    executed_qty = sum(qty for qty, _ in executions)
    vwap = (total / executed_qty) if executed_qty > 0 else None
    return executions, remaining, total, vwap


def _levels_table_html(title: str, levels: list[tuple[float, float]], tone: str) -> str:
    rows = "".join(
        (
            "<tr>"
            f"<td>{price:.4f}</td>"
            f"<td>{qty:.2f}</td>"
            "</tr>"
        )
        for price, qty in levels[:10]
    )
    if not rows:
        rows = '<tr><td colspan="2">No levels</td></tr>'

    return (
        f'<div class="ob-panel ob-panel--{tone}">'
        f'<div class="ob-panel__title">{title}</div>'
        '<table class="ob-table">'
        "<thead><tr><th>Price</th><th>Qty</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
    )


def _build_depth_chart_for_outcome(book: dict, outcome: str) -> go.Figure:
    asks = list(book.get("asks", []))
    bids = list(book.get("bids", []))

    def cumulative(levels: list[tuple[float, float]]) -> tuple[list[float], list[float]]:
        qty_cum: list[float] = []
        prices: list[float] = []
        total = 0.0
        for price, qty in levels:
            total += float(qty)
            qty_cum.append(total)
            prices.append(float(price))
        return qty_cum, prices

    asks_x, asks_y = cumulative(asks)
    bids_x, bids_y = cumulative(bids)

    fig = go.Figure()
    if asks_x and asks_y:
        fig.add_trace(
            go.Scatter(
                x=asks_x,
                y=asks_y,
                mode="lines",
                name="Asks",
                line={"color": "#b5474f", "width": 2, "shape": "hv"},
                fill="tozerox",
                fillcolor="rgba(181,71,79,0.16)",
            )
        )
    if bids_x and bids_y:
        fig.add_trace(
            go.Scatter(
                x=bids_x,
                y=bids_y,
                mode="lines",
                name="Bids",
                line={"color": "#18794e", "width": 2, "shape": "hv"},
                fill="tozerox",
                fillcolor="rgba(24,121,78,0.16)",
            )
        )

    fig.update_layout(
        title=f"Depth - {outcome}",
        title_font={"color": "#111111"},
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Cumulative quantity",
        yaxis_title="Price",
        legend={"orientation": "h", "y": 1.02, "x": 0, "font": {"color": "#111111"}},
        height=330,
    )
    return fig


def _render_depth_charts(orderbook_by_outcome: dict[str, dict]) -> None:
    outcomes = list(orderbook_by_outcome.keys())
    if not outcomes:
        return

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    st.markdown("#### Depth charts")

    per_row = 2
    for start in range(0, len(outcomes), per_row):
        row_outcomes = outcomes[start : start + per_row]
        columns = st.columns(len(row_outcomes))
        for column, outcome in zip(columns, row_outcomes):
            with column:
                chart = _build_depth_chart_for_outcome(
                    orderbook_by_outcome.get(outcome, {}),
                    outcome,
                )
                st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})


def _render_orderbook_block(orderbook_by_outcome: dict[str, dict]) -> None:
    outcomes = list(orderbook_by_outcome.keys())
    if not outcomes:
        render_info_card(
            "Order book unavailable",
            "No orderbook levels available for this market yet.",
            tone="warning",
        )
        return

    st.markdown(
        """
        <style>
        .ob-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.65rem;
        }
        .ob-panel {
            border: 1px solid #d6e3eb;
            border-radius: 14px;
            overflow: hidden;
            background: #fbfdfe;
        }
        .ob-panel__title {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 0.45rem 0.65rem;
        }
        .ob-panel--ask .ob-panel__title {
            color: #b5474f;
            background: #f9e1e4;
        }
        .ob-panel--bid .ob-panel__title {
            color: #18794e;
            background: #dbf2e5;
        }
        .ob-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }
        .ob-table th,
        .ob-table td {
            padding: 0.36rem 0.58rem;
            text-align: right;
            color: #12354a;
            font-size: 0.86rem;
        }
        .ob-table th {
            font-weight: 700;
            color: #5b7486;
            border-bottom: 1px solid #d6e3eb;
        }
        .ob-table tbody tr + tr td {
            border-top: 1px solid #edf3f7;
        }
        .ob-table tbody tr td:first-child,
        .ob-table thead tr th:first-child {
            text-align: left;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(outcomes))
    for column, outcome in zip(columns, outcomes):
        with column:
            book = orderbook_by_outcome.get(outcome, {})
            asks = book.get("asks", [])[:8]
            bids = book.get("bids", [])[:8]

            st.markdown(f"#### {outcome}")
            if not asks and not bids:
                st.caption("No levels")
                continue

            st.markdown(
                (
                    '<div class="ob-grid">'
                    f'{_levels_table_html("Asks", asks, "ask")}'
                    f'{_levels_table_html("Bids", bids, "bid")}'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )


def _refresh_orderbook(api: APIClient, market: dict, token: str | None) -> dict:
    asset_ids = [str(asset_id) for asset_id in market.get("clob_token_ids", []) if asset_id]
    if asset_ids:
        try:
            api.start_stream(asset_ids, token=token)
            st.session_state.market_stream_started = True
            st.session_state.active_market_slug = str(market.get("slug"))
        except APIClientError:
            pass

    raw_orderbook = api.get_orderbook(token=token)
    st.session_state.orderbook = raw_orderbook
    return raw_orderbook


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
            token=token,
        )
        markets = [_normalize_market(m) for m in listing.get("items", [])]
        total_pages = int(listing.get("total_pages", 1) or 1)
    except APIClientError:
        markets = [_normalize_market(m) for m in api.get_markets(token=token)]
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
        market = api.get_market(slug, token=token)
        return _normalize_market(market)
    except APIClientError:
        pass
    for market in api.get_markets(token=token):
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

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    render_section_header(
        "Order book",
        "Use orderbook levels as execution prices, with refresh and visibility controls.",
    )

    show_key = f"show_orderbook_{slug}"
    if show_key not in st.session_state:
        st.session_state[show_key] = False

    col_show, col_refresh = st.columns([1.0, 1.0])
    with col_show:
        show_label = "Hide orderbook" if st.session_state[show_key] else "Show orderbook"
        if st.button(show_label, key=f"toggle_orderbook_{slug}", use_container_width=True):
            st.session_state[show_key] = not st.session_state[show_key]
            st.rerun()
    with col_refresh:
        if st.button(
            "Refresh orderbook",
            key=f"refresh_orderbook_{slug}",
            use_container_width=True,
        ):
            try:
                _refresh_orderbook(api, market, token)
            except APIClientError as exc:
                render_api_error_state(exc, resource="order book")
                return
            st.rerun()

    raw_orderbook = st.session_state.get("orderbook")
    if raw_orderbook is None and st.session_state[show_key]:
        try:
            raw_orderbook = _refresh_orderbook(api, market, token)
        except APIClientError:
            raw_orderbook = None

    orderbook_by_outcome = _map_orderbook_by_outcome(raw_orderbook, market)

    if st.session_state[show_key]:
        _render_orderbook_block(orderbook_by_outcome)
        _render_depth_charts(orderbook_by_outcome)

    render_section_header(
        "Trade ticket",
        "Execution price is driven by orderbook levels, as in the legacy trading flow.",
    )
    portfolio_ids = [str(p.get("id") or p.get("_id")) for p in portfolios]
    if not portfolio_ids:
        render_info_card(
            "No portfolio available",
            "Create a portfolio before submitting a trade.",
            tone="warning",
        )
        if st.button("Create portfolio", key="create_portfolio_from_trade"):
            st.session_state.nav_override = "Portfolio"
            st.rerun()
        return

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

    book = orderbook_by_outcome.get(outcome, {})
    level_side = "asks" if action == "BUY" else "bids"
    levels = list(book.get(level_side, []))
    best_price = levels[0][0] if levels else None

    qty = st.number_input("Quantity", min_value=1.0, value=1.0, step=1.0)
    note = st.text_input("Note (optional)", value="")
    if best_price is None:
        st.warning("No executable levels in the orderbook for this token/side.")
        st.caption("Use Show/Refresh orderbook to fetch live levels.")
    else:
        executions, remaining, total_cost, vwap = _estimate_executions(levels, float(qty))
        vwap_text = format_probability(vwap) if vwap is not None else "-"
        st.caption(
            f"Best {level_side[:-1]}: {format_probability(best_price)} | "
            f"VWAP: {vwap_text} | Notional: ${total_cost:,.2f}"
        )
        if remaining > 0:
            st.warning(
                f"Partial fill expected: {format_quantity(float(qty) - remaining)} / "
                f"{format_quantity(qty)} available in the book."
            )

    if st.button("Submit trade", type="primary", disabled=best_price is None):
        if not selected_portfolio_id:
            st.error("Create a portfolio before submitting a trade.")
            return

        market_id = str(market.get("id") or market.get("slug"))
        executions, _, _, _ = _estimate_executions(levels, float(qty))
        if not executions:
            st.error("Orderbook has no available levels for execution.")
            return

        try:
            for exec_qty, exec_price in executions:
                api.create_trade(
                    portfolio_id=selected_portfolio_id,
                    market_id=market_id,
                    outcome=outcome,
                    action=action,
                    qty=float(exec_qty),
                    price=float(exec_price),
                    token=token,
                    notes=note or None,
                )
        except APIClientError as exc:
            render_api_error_state(exc, resource="trade creation")
            return
        st.session_state.trade_submit_success_message = "Trade submitted"
        st.session_state.trade_submit_success_animate = True
        st.rerun()


def render(api: APIClient) -> None:
    if st.session_state.get("trade_submit_success_animate"):
        st.success(st.session_state.get("trade_submit_success_message") or "Trade submitted")
        st.balloons()
        st.session_state.trade_submit_success_animate = False
        st.session_state.trade_submit_success_message = None

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
