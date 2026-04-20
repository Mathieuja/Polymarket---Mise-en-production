from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from app_shared.database import Market, Portfolio, Trade
from sqlalchemy.orm import Session

from app.backend.api.schemas.portfolio import (
    MarkToMarketResponse,
    PortfolioCreate,
    PortfolioMetrics,
    PortfolioResponse,
    PortfolioUpdate,
    PortfolioWithPositions,
    Position,
)
from app.backend.api.schemas.trade import TradeCreate, TradeHistory, TradeResponse


@dataclass(frozen=True)
class _PositionState:
    quantity: float = 0.0
    total_cost: float = 0.0


class PortfolioService:
    """PostgreSQL-backed portfolio and trade service."""

    def __init__(self, db: Session):
        self.db = db

    def list_portfolios(self, user_id: int) -> list[PortfolioResponse]:
        portfolios = (
            self.db.query(Portfolio)
            .filter(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
            .all()
        )
        return [self._serialize_portfolio(portfolio) for portfolio in portfolios]

    def create_portfolio(self, user_id: int, body: PortfolioCreate) -> PortfolioResponse:
        portfolio = Portfolio(
            user_id=user_id,
            name=body.name.strip(),
            description=body.description,
            initial_balance=float(body.initial_balance),
            is_active=True,
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return self._serialize_portfolio(portfolio)

    def get_portfolio(self, portfolio_id: int, user_id: int) -> PortfolioResponse | None:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None
        return self._serialize_portfolio(portfolio)

    def update_portfolio(
        self,
        portfolio_id: int,
        user_id: int,
        body: PortfolioUpdate,
    ) -> PortfolioResponse | None:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        for field_name, value in body.model_dump(exclude_unset=True).items():
            setattr(portfolio, field_name, value)

        self.db.commit()
        self.db.refresh(portfolio)
        return self._serialize_portfolio(portfolio)

    def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return False

        self.db.query(Trade).filter(Trade.portfolio_id == portfolio.id).delete()
        self.db.delete(portfolio)
        self.db.commit()
        return True

    def add_trade(self, portfolio_id: int, user_id: int, body: TradeCreate) -> TradeResponse | None:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        side = str(body.side).strip().lower()
        if side not in {"buy", "sell"}:
            raise ValueError("Action must be buy or sell")

        if side == "sell":
            position_qty = self._position_qty(portfolio_id, body.market_id, body.outcome)
            if position_qty < float(body.quantity):
                raise ValueError("Insufficient position to sell")

        trade = Trade(
            portfolio_id=portfolio.id,
            market_id=body.market_id.strip(),
            outcome=body.outcome.strip(),
            side=side,
            quantity=float(body.quantity),
            price=float(body.price),
            trade_timestamp=datetime.now(timezone.utc),
            notes=body.notes,
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return self._serialize_trade(trade)

    def get_trades(
        self,
        portfolio_id: int,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> TradeHistory:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return TradeHistory(
                trades=[], total=0, page=page, page_size=page_size, has_more=False
            )

        query = self.db.query(Trade).filter(Trade.portfolio_id == portfolio.id)
        total = query.count()
        trades = (
            query.order_by(Trade.trade_timestamp.desc(), Trade.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return TradeHistory(
            trades=[self._serialize_trade(trade) for trade in trades],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    def calculate_metrics(self, portfolio_id: int, user_id: int) -> PortfolioMetrics | None:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        trades = self._portfolio_trades(portfolio.id)
        cash_balance = self._cash_balance(portfolio.initial_balance, trades)
        positions_value = self._positions_value(trades)
        total_value = cash_balance + positions_value
        total_pnl = total_value - float(portfolio.initial_balance)
        total_pnl_percent = (
            (total_pnl / float(portfolio.initial_balance)) * 100.0
            if float(portfolio.initial_balance) > 0
            else 0.0
        )

        return PortfolioMetrics(
            portfolio_id=portfolio.id,
            cash_balance=cash_balance,
            positions_value=positions_value,
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            trades_count=len(trades),
        )

    def calculate_mtm(
        self,
        portfolio_id: int,
        user_id: int,
        resolution: int = 60,
    ) -> MarkToMarketResponse | None:
        metrics = self.calculate_metrics(portfolio_id, user_id)
        if metrics is None:
            return None

        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        return MarkToMarketResponse(
            portfolio_id=portfolio.id,
            as_of=datetime.now(timezone.utc),
            initial_balance=float(portfolio.initial_balance),
            cash_balance=metrics.cash_balance,
            current_value=metrics.total_value,
            pnl=metrics.total_pnl,
            pnl_percent=metrics.total_pnl_percent,
            total_trades=metrics.trades_count,
            resolution=resolution,
        )

    def get_portfolio_with_positions(
        self,
        portfolio_id: int,
        user_id: int,
    ) -> PortfolioWithPositions | None:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        trades = self._portfolio_trades(portfolio.id)
        cash_balance = self._cash_balance(portfolio.initial_balance, trades)

        states: dict[tuple[str, str], _PositionState] = defaultdict(_PositionState)
        for trade in trades:
            key = (trade.market_id, trade.outcome.upper())
            state = states[key]
            if trade.side == "buy":
                states[key] = _PositionState(
                    quantity=state.quantity + trade.quantity,
                    total_cost=state.total_cost + trade.quantity * trade.price,
                )
            else:
                qty = min(state.quantity, trade.quantity)
                if qty <= 0:
                    continue
                avg_price = state.total_cost / state.quantity if state.quantity > 0 else 0.0
                states[key] = _PositionState(
                    quantity=max(0.0, state.quantity - qty),
                    total_cost=max(0.0, state.total_cost - (avg_price * qty)),
                )

        positions: list[Position] = []
        for (market_id, outcome), state in states.items():
            if state.quantity <= 0:
                continue
            average_price = state.total_cost / state.quantity if state.quantity > 0 else 0.0
            current_price = self._current_market_price(market_id, outcome) or average_price
            positions.append(
                Position(
                    market_id=market_id,
                    outcome=outcome,
                    quantity=state.quantity,
                    average_price=average_price,
                    current_price=current_price,
                    unrealized_pnl=state.quantity * (current_price - average_price),
                )
            )

        total_positions_value = sum(
            position.quantity * position.current_price for position in positions
        )
        total_value = cash_balance + total_positions_value
        total_pnl = total_value - float(portfolio.initial_balance)
        total_pnl_percent = (
            (total_pnl / float(portfolio.initial_balance)) * 100.0
            if float(portfolio.initial_balance) > 0
            else 0.0
        )

        return PortfolioWithPositions(
            **self._serialize_portfolio(portfolio).model_dump(),
            positions=positions,
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
        )

    def _get_owned_portfolio(self, portfolio_id: int, user_id: int) -> Portfolio | None:
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .first()
        )

    def _portfolio_trades(self, portfolio_id: int) -> list[Trade]:
        return (
            self.db.query(Trade)
            .filter(Trade.portfolio_id == portfolio_id)
            .order_by(Trade.trade_timestamp.asc(), Trade.id.asc())
            .all()
        )

    def _cash_balance(self, initial_balance: float, trades: list[Trade]) -> float:
        cash_balance = float(initial_balance)
        for trade in trades:
            delta = float(trade.quantity) * float(trade.price)
            cash_balance += delta if trade.side == "sell" else -delta
        return cash_balance

    def _position_qty(self, portfolio_id: int, market_id: str, outcome: str) -> float:
        quantity = 0.0
        for trade in self._portfolio_trades(portfolio_id):
            if str(trade.market_id) != str(market_id):
                continue
            if str(trade.outcome).upper() != str(outcome).upper():
                continue
            quantity += float(trade.quantity) if trade.side == "buy" else -float(trade.quantity)
        return quantity

    def _positions_value(self, trades: list[Trade]) -> float:
        quantities: dict[tuple[str, str], float] = defaultdict(float)
        for trade in trades:
            key = (trade.market_id, trade.outcome.upper())
            quantities[key] += float(trade.quantity) if trade.side == "buy" else -float(trade.quantity)

        total = 0.0
        for (market_id, outcome), quantity in quantities.items():
            if quantity <= 0:
                continue
            price = self._current_market_price(market_id, outcome)
            if price is None:
                continue
            total += quantity * price
        return total

    def _current_market_price(self, market_id: str, outcome: str) -> float | None:
        market = (
            self.db.query(Market)
            .filter((Market.slug == market_id) | (Market.condition_id == market_id))
            .first()
        )
        if market is None:
            return None

        outcomes = market.outcomes or []
        prices = market.outcome_prices or []
        for index, market_outcome in enumerate(outcomes):
            if index >= len(prices):
                continue
            if str(market_outcome).upper() != str(outcome).upper():
                continue
            try:
                return float(prices[index])
            except (TypeError, ValueError):
                return None
        return None

    def _serialize_portfolio(self, portfolio: Portfolio) -> PortfolioResponse:
        cash_balance = self._cash_balance(
            portfolio.initial_balance,
            self._portfolio_trades(portfolio.id),
        )
        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            description=portfolio.description,
            initial_balance=float(portfolio.initial_balance),
            cash_balance=cash_balance,
            is_active=portfolio.is_active,
            created_at=portfolio.created_at,
        )

    def _serialize_trade(self, trade: Trade) -> TradeResponse:
        return TradeResponse(
            id=trade.id,
            portfolio_id=trade.portfolio_id,
            market_id=trade.market_id,
            outcome=trade.outcome,
            side=trade.side,
            quantity=float(trade.quantity),
            price=float(trade.price),
            trade_timestamp=trade.trade_timestamp,
            created_at=trade.created_at,
            notes=trade.notes,
        )