from __future__ import annotations

import pytest

from app.utils.portfolio_math import (
    can_sell,
    compute_portfolio_metrics,
    compute_positions,
    market_outcome_price_usd,
    position_qty,
)


def test_market_outcome_price_yes_no():
    market = {"id": "m1", "prices": [{"t": "t1", "price": 0.7}]}
    assert market_outcome_price_usd(market, "YES") == 0.7
    assert market_outcome_price_usd(market, "NO") == pytest.approx(0.3)


def test_compute_positions_buy_sell():
    trades = [
        {"portfolio_id": "pf-1", "market_id": "m1", "outcome": "YES", "action": "BUY", "qty": 3},
        {"portfolio_id": "pf-1", "market_id": "m1", "outcome": "YES", "action": "SELL", "qty": 1},
        {"portfolio_id": "pf-1", "market_id": "m2", "outcome": "NO", "action": "BUY", "qty": 2},
    ]
    pos = compute_positions(trades)
    assert pos[("pf-1", "m1", "YES")] == 2
    assert pos[("pf-1", "m2", "NO")] == 2


def test_position_qty_and_can_sell():
    trades = [
        {"portfolio_id": "pf-1", "market_id": "m1", "outcome": "YES", "action": "BUY", "qty": 2},
        {"portfolio_id": "pf-1", "market_id": "m1", "outcome": "YES", "action": "SELL", "qty": 1},
    ]
    assert position_qty(trades, "pf-1", "m1", "YES") == 1
    assert can_sell(trades, "pf-1", "m1", "YES", 1) is True
    assert can_sell(trades, "pf-1", "m1", "YES", 2) is False


def test_compute_portfolio_metrics_basic():
    portfolio = {"id": "pf-1", "cash_usd": 900.0, "initial_cash_usd": 1000.0}
    markets = [
        {"id": "m1", "prices": [{"t": "t1", "price": 0.5}]},
        {"id": "m2", "prices": [{"t": "t1", "price": 0.2}]},
    ]
    trades = [
        {
            "portfolio_id": "pf-1",
            "market_id": "m1",
            "outcome": "YES",
            "action": "BUY",
            "qty": 10,
            "price": 0.5,
        },
        {
            "portfolio_id": "pf-1",
            "market_id": "m2",
            "outcome": "NO",
            "action": "BUY",
            "qty": 5,
            "price": 0.8,
        },
    ]

    metrics = compute_portfolio_metrics(portfolio=portfolio, trades=trades, markets=markets)
    # Positions: 10 YES @ 0.5 -> 5.0; 5 NO where YES=0.2 -> NO=0.8 -> 4.0
    assert metrics.positions_value_usd == 9.0
    assert metrics.total_value_usd == 909.0
    assert metrics.pnl_usd == -91.0


def test_pnl_is_zero_when_marked_at_entry_price():
    markets = [{"id": "m1", "prices": [{"t": "t1", "price": 0.4}]}]

    # If we buy 10 YES at 0.4, and mark at 0.4, total value stays 1000.
    # We'll represent the post-trade cash state (like the app does).
    trades = [
        {
            "portfolio_id": "pf-1",
            "market_id": "m1",
            "outcome": "YES",
            "action": "BUY",
            "qty": 10,
            "price": 0.4,
        }
    ]
    portfolio_after = {"id": "pf-1", "cash_usd": 1000.0 - 10 * 0.4, "initial_cash_usd": 1000.0}
    metrics = compute_portfolio_metrics(portfolio=portfolio_after, trades=trades, markets=markets)
    assert metrics.total_value_usd == pytest.approx(1000.0)
    assert metrics.pnl_usd == pytest.approx(0.0)
