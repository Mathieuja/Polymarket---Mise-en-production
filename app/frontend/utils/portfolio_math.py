from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class PortfolioMetrics:
    cash_usd: float
    positions_value_usd: float
    total_value_usd: float
    pnl_usd: float


def compute_positions(trades: Iterable[dict[str, Any]]) -> dict[tuple[str, str, str], float]:
    """Return position size keyed by (portfolio_id, market_id, outcome).

    outcome is expected to be "YES" or "NO".
    action is expected to be "BUY" or "SELL".
    """

    positions: dict[tuple[str, str, str], float] = {}
    for t in trades:
        portfolio_id = str(t["portfolio_id"])
        market_id = str(t["market_id"])
        outcome = str(t.get("outcome") or t.get("side") or "YES").upper()
        action = str(t.get("action", "BUY")).upper()
        qty = float(t.get("qty", 0.0))

        key = (portfolio_id, market_id, outcome)
        prev = positions.get(key, 0.0)

        if action == "BUY":
            positions[key] = prev + qty
        elif action == "SELL":
            positions[key] = prev - qty
        else:
            # unknown action, ignore
            positions[key] = prev

    # Clean near-zero
    return {k: v for k, v in positions.items() if abs(v) > 1e-12}


def position_qty(
    trades: Iterable[dict[str, Any]],
    portfolio_id: str,
    market_id: str,
    outcome: str,
) -> float:
    outcome = outcome.upper()
    positions = compute_positions(trades)
    return float(positions.get((str(portfolio_id), str(market_id), outcome), 0.0))


def can_sell(
    trades: Iterable[dict[str, Any]],
    portfolio_id: str,
    market_id: str,
    outcome: str,
    qty: float,
) -> bool:
    """True if portfolio holds enough position to sell qty (no shorting)."""

    if qty <= 0:
        return False
    return position_qty(trades, portfolio_id, market_id, outcome) >= float(qty)


def market_outcome_price_usd(market: dict[str, Any], outcome: str) -> float:
    """Get last known outcome price in USD (0..1) from mock market structure.

    For mock fixtures, market has prices=[{t, price}] which we interpret as YES price.
    NO price is (1 - YES).
    """

    outcome = outcome.upper()
    prices = market.get("prices")
    if not isinstance(prices, list) or not prices:
        yes_price = float(market.get("price", 0.5))
    else:
        last = prices[-1]
        yes_price = float(last.get("price", 0.5))

    if outcome == "YES":
        return yes_price
    return 1.0 - yes_price


def compute_portfolio_metrics(
    portfolio: dict[str, Any],
    trades: Iterable[dict[str, Any]],
    markets: list[dict[str, Any]],
) -> PortfolioMetrics:
    cash = float(portfolio.get("cash_usd", 0.0))
    initial_cash = float(portfolio.get("initial_cash_usd", cash))

    market_by_id = {str(m.get("id")): m for m in markets}
    positions = compute_positions(trades)

    positions_value = 0.0
    for (portfolio_id, market_id, outcome), qty in positions.items():
        if str(portfolio.get("id")) != portfolio_id:
            continue
        market = market_by_id.get(market_id)
        if not market:
            continue
        positions_value += qty * market_outcome_price_usd(market, outcome)

    total_value = cash + positions_value
    pnl = total_value - initial_cash

    return PortfolioMetrics(
        cash_usd=cash,
        positions_value_usd=positions_value,
        total_value_usd=total_value,
        pnl_usd=pnl,
    )
