from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app_shared.database import Market, Portfolio, Trade
from sqlalchemy.orm import Session

from app.backend.api.schemas.portfolio import (
    MarkToMarketResponse,
    MTMPnLSnapshot,
    MTMPositionSeries,
    PnLDataPoint,
    PortfolioCreate,
    PortfolioMetrics,
    PortfolioResponse,
    PortfolioUpdate,
    PortfolioWithPositions,
    Position,
    PositionPnLHistory,
)
from app.backend.api.schemas.trade import TradeCreate, TradeHistory, TradeResponse


@dataclass
class _PositionAccumulator:
    quantity: float = 0.0
    total_cost: float = 0.0
    realized_pnl: float = 0.0
    first_trade_at: Optional[datetime] = None


class PortfolioService:
    """PostgreSQL-backed portfolio/trade service compatible with legacy endpoints."""

    def __init__(self, db: Session):
        self.db = db

    async def create_portfolio(self, user_id: int, request: PortfolioCreate) -> PortfolioResponse:
        portfolio = Portfolio(
            user_id=user_id,
            name=request.name,
            description=request.description,
            initial_balance=request.initial_balance,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return self._portfolio_to_response(portfolio, cash_balance=portfolio.initial_balance)

    async def get_portfolio(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .first()
        )

    async def list_portfolios(self, user_id: int) -> list[PortfolioResponse]:
        portfolios = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
        responses: list[PortfolioResponse] = []
        for portfolio in portfolios:
            cash = await self._calculate_cash_balance(portfolio.id, portfolio.initial_balance)
            responses.append(self._portfolio_to_response(portfolio, cash_balance=cash))
        return responses

    async def update_portfolio(
        self,
        portfolio_id: int,
        user_id: int,
        request: PortfolioUpdate,
    ) -> Optional[PortfolioResponse]:
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        updates = request.model_dump(exclude_none=True)
        for key, value in updates.items():
            setattr(portfolio, key, value)

        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)

        cash = await self._calculate_cash_balance(portfolio.id, portfolio.initial_balance)
        return self._portfolio_to_response(portfolio, cash_balance=cash)

    async def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return False

        self.db.query(Trade).filter(Trade.portfolio_id == portfolio.id).delete()
        self.db.delete(portfolio)
        self.db.commit()
        return True

    async def add_trade(
        self,
        portfolio_id: int,
        user_id: int,
        request: TradeCreate,
    ) -> Optional[TradeResponse]:
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        trade = Trade(
            portfolio_id=portfolio.id,
            market_id=request.market_id,
            outcome=request.outcome,
            side=request.side.value,
            quantity=request.quantity,
            price=request.price,
            trade_timestamp=request.trade_timestamp or datetime.utcnow(),
            created_at=datetime.utcnow(),
            notes=request.notes,
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return self._trade_to_response(trade)

    async def get_trades(
        self,
        portfolio_id: int,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TradeHistory:
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return TradeHistory(trades=[], total=0, page=page, page_size=page_size, has_more=False)

        query = self.db.query(Trade).filter(Trade.portfolio_id == portfolio.id)
        if start_date is not None:
            query = query.filter(Trade.trade_timestamp >= start_date)
        if end_date is not None:
            query = query.filter(Trade.trade_timestamp <= end_date)

        total = query.count()
        skip = (page - 1) * page_size
        trades = (
            query.order_by(Trade.trade_timestamp.desc())
            .offset(skip)
            .limit(page_size)
            .all()
        )

        items = [self._trade_to_response(item) for item in trades]
        return TradeHistory(
            trades=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(skip + len(items)) < total,
        )

    async def get_portfolio_with_positions(
        self,
        portfolio_id: int,
        user_id: int,
    ) -> Optional[PortfolioWithPositions]:
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if portfolio is None:
            return None

        trades = (
            self.db.query(Trade)
            .filter(Trade.portfolio_id == portfolio.id)
            .order_by(Trade.trade_timestamp.asc())
            .all()
        )
        positions = await self._calculate_positions(trades)

        initial_balance = float(portfolio.initial_balance)
        cash_balance = await self._calculate_cash_balance(portfolio.id, initial_balance)

        position_value = 0.0
        for position in positions:
            mark_price = (
                position.current_price
                if position.current_price is not None
                else position.average_price
            )
            position_value += position.quantity * mark_price

        total_value = cash_balance + position_value
        total_pnl = total_value - initial_balance
        total_pnl_percent = (total_pnl / initial_balance * 100.0) if initial_balance > 0 else 0.0

        base = self._portfolio_to_response(portfolio, cash_balance=cash_balance)
        return PortfolioWithPositions(
            **base.model_dump(),
            positions=positions,
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
        )

    async def calculate_metrics(
        self,
        portfolio_id: int,
        user_id: int,
        as_of: Optional[datetime] = None,
    ) -> Optional[PortfolioMetrics]:
        _ = as_of
        details = await self.get_portfolio_with_positions(portfolio_id, user_id)
        if details is None:
            return None

        trades = (
            self.db.query(Trade)
            .filter(Trade.portfolio_id == int(portfolio_id))
            .order_by(Trade.trade_timestamp.asc())
            .all()
        )

        realized = self._compute_realized_trade_pnls(trades)
        cumulative = 0.0
        history = []
        for index, value in enumerate(realized):
            cumulative += value
            timestamp = trades[index].trade_timestamp if index < len(trades) else datetime.utcnow()
            history.append(PnLDataPoint(timestamp=timestamp, pnl=value, cumulative_pnl=cumulative))

        win_rate = None
        if realized:
            wins = len([p for p in realized if p > 0])
            win_rate = (wins / len(realized)) * 100.0

        positions_history = [
            PositionPnLHistory(
                market_id=pos.market_id,
                outcome=pos.outcome,
                market_question=pos.market_question,
                current_quantity=pos.quantity,
                average_cost=pos.average_price,
                current_price=pos.current_price,
                unrealized_pnl=pos.unrealized_pnl,
                realized_pnl=0.0,
                total_pnl=(pos.unrealized_pnl or 0.0),
            )
            for pos in details.positions
        ]

        return PortfolioMetrics(
            portfolio_id=str(portfolio_id),
            as_of=datetime.now(timezone.utc),
            total_value=details.total_value,
            cash_balance=details.cash_balance,
            initial_balance=details.initial_balance,
            total_pnl=details.total_pnl,
            total_pnl_percent=details.total_pnl_percent,
            sharpe_ratio=None,
            volatility=None,
            max_drawdown=None,
            win_rate=win_rate,
            total_trades=len(trades),
            avg_trade_pnl=(sum(realized) / len(realized)) if realized else None,
            best_trade=max(realized) if realized else None,
            worst_trade=min(realized) if realized else None,
            pnl_history=history,
            drawdown_history=[],
            positions=positions_history,
        )

    async def mark_to_market(
        self,
        portfolio_id: int,
        user_id: int,
        resolution_minutes: int = 60,
    ) -> Optional[MarkToMarketResponse]:
        _ = resolution_minutes
        details = await self.get_portfolio_with_positions(portfolio_id, user_id)
        if details is None:
            return None

        snapshot = MTMPnLSnapshot(
            timestamp=datetime.now(timezone.utc),
            portfolio_value=details.total_value,
            cash_balance=details.cash_balance,
            position_value=details.total_value - details.cash_balance,
            unrealized_pnl=sum((p.unrealized_pnl or 0.0) for p in details.positions),
            realized_pnl=0.0,
            total_pnl=details.total_pnl,
            total_pnl_percent=details.total_pnl_percent,
        )

        positions = []
        for pos in details.positions:
            current_price = (
                pos.current_price
                if pos.current_price is not None
                else pos.average_price
            )
            unrealized = pos.unrealized_pnl if pos.unrealized_pnl is not None else 0.0
            positions.append(
                MTMPositionSeries(
                    market_id=pos.market_id,
                    outcome=pos.outcome,
                    market_question=pos.market_question,
                    current_quantity=pos.quantity,
                    average_entry_price=pos.average_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized,
                    realized_pnl=0.0,
                    total_pnl=unrealized,
                    first_trade_at=None,
                    timestamps=[snapshot.timestamp],
                    prices=[current_price],
                    unrealized_pnls=[unrealized],
                    total_pnls=[unrealized],
                )
            )

        return MarkToMarketResponse(
            portfolio_id=str(portfolio_id),
            as_of=snapshot.timestamp,
            initial_balance=details.initial_balance,
            cash_balance=details.cash_balance,
            total_value=details.total_value,
            total_pnl=details.total_pnl,
            total_pnl_percent=details.total_pnl_percent,
            sharpe_ratio=None,
            volatility=None,
            max_drawdown=None,
            win_rate=None,
            total_trades=0,
            avg_trade_pnl=None,
            best_trade=None,
            worst_trade=None,
            pnl_series=[snapshot],
            positions=positions,
        )

    async def _calculate_positions(self, trades: list[Trade]) -> list[Position]:
        acc: dict[tuple[str, str], _PositionAccumulator] = defaultdict(_PositionAccumulator)
        market_questions: dict[str, Optional[str]] = {}

        for trade in trades:
            key = (trade.market_id, trade.outcome)
            state = acc[key]
            if state.first_trade_at is None:
                state.first_trade_at = trade.trade_timestamp

            if trade.side == "buy":
                state.quantity += trade.quantity
                state.total_cost += trade.quantity * trade.price
            else:
                if state.quantity <= 0:
                    continue
                average = state.total_cost / state.quantity
                qty = min(trade.quantity, state.quantity)
                state.realized_pnl += (trade.price - average) * qty
                state.quantity -= qty
                state.total_cost -= average * qty

            market = self._get_market(trade.market_id)
            market_questions[trade.market_id] = market.question if market else None

        positions: list[Position] = []
        for (market_id, outcome), state in acc.items():
            if state.quantity <= 0:
                continue

            average = (state.total_cost / state.quantity) if state.quantity > 0 else 0.0
            current_price = self._get_current_price(market_id, outcome)
            unrealized = (
                state.quantity * (current_price - average)
                if current_price is not None
                else None
            )

            positions.append(
                Position(
                    market_id=market_id,
                    outcome=outcome,
                    quantity=state.quantity,
                    average_price=average,
                    current_price=current_price,
                    unrealized_pnl=unrealized,
                    market_question=market_questions.get(market_id),
                )
            )

        return positions

    async def _calculate_cash_balance(self, portfolio_id: int, initial_balance: float) -> float:
        trades = self.db.query(Trade).filter(Trade.portfolio_id == portfolio_id).all()
        spent = 0.0
        for trade in trades:
            amount = trade.quantity * trade.price
            spent += amount if trade.side == "buy" else -amount
        return float(initial_balance) - spent

    def _compute_realized_trade_pnls(self, trades: list[Trade]) -> list[float]:
        acc: dict[tuple[str, str], _PositionAccumulator] = defaultdict(_PositionAccumulator)
        realized: list[float] = []

        for trade in trades:
            key = (trade.market_id, trade.outcome)
            state = acc[key]
            if trade.side == "buy":
                state.quantity += trade.quantity
                state.total_cost += trade.quantity * trade.price
                continue

            if state.quantity <= 0:
                continue
            average = state.total_cost / state.quantity
            qty = min(trade.quantity, state.quantity)
            pnl = (trade.price - average) * qty
            state.quantity -= qty
            state.total_cost -= average * qty
            realized.append(pnl)

        return realized

    def _get_market(self, market_id: str) -> Optional[Market]:
        return (
            self.db.query(Market)
            .filter((Market.slug == market_id) | (Market.condition_id == market_id))
            .first()
        )

    def _get_current_price(self, market_id: str, outcome: str) -> Optional[float]:
        market = self._get_market(market_id)
        if not market:
            return None

        outcomes = market.outcomes or []
        prices = market.outcome_prices or []
        for index, candidate in enumerate(outcomes):
            if candidate == outcome and index < len(prices):
                try:
                    return float(prices[index])
                except (TypeError, ValueError):
                    return None
        return None

    def _trade_to_response(self, trade: Trade) -> TradeResponse:
        market = self._get_market(trade.market_id)
        return TradeResponse(
            id=str(trade.id),
            portfolio_id=str(trade.portfolio_id),
            market_id=trade.market_id,
            outcome=trade.outcome,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            total_value=trade.quantity * trade.price,
            trade_timestamp=trade.trade_timestamp,
            created_at=trade.created_at,
            notes=trade.notes,
            market_question=market.question if market else None,
        )

    def _portfolio_to_response(
        self,
        portfolio: Portfolio,
        cash_balance: float,
    ) -> PortfolioResponse:
        return PortfolioResponse(
            id=str(portfolio.id),
            user_id=str(portfolio.user_id),
            name=portfolio.name,
            description=portfolio.description,
            initial_balance=portfolio.initial_balance,
            cash_balance=cash_balance,
            created_at=portfolio.created_at,
            is_active=portfolio.is_active,
        )
