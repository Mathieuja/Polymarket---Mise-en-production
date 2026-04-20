from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    initial_balance: float = Field(default=10000.0, gt=0)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class PortfolioResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    initial_balance: float
    cash_balance: float
    created_at: datetime
    is_active: bool


class Position(BaseModel):
    market_id: str
    outcome: str
    quantity: float
    average_price: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    market_question: Optional[str] = None


class PortfolioWithPositions(PortfolioResponse):
    positions: list[Position] = Field(default_factory=list)
    total_value: float
    cash_balance: float
    total_pnl: float
    total_pnl_percent: float


class PnLDataPoint(BaseModel):
    timestamp: datetime
    pnl: float
    cumulative_pnl: float


class PositionPnLHistory(BaseModel):
    market_id: str
    outcome: str
    market_question: Optional[str] = None
    current_quantity: float
    average_cost: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    pnl_history: list[PnLDataPoint] = Field(default_factory=list)


class PortfolioMetrics(BaseModel):
    portfolio_id: str
    as_of: datetime
    total_value: float
    cash_balance: float
    initial_balance: float
    total_pnl: float
    total_pnl_percent: float
    sharpe_ratio: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_trades: int = 0
    avg_trade_pnl: Optional[float] = None
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None
    pnl_history: list[PnLDataPoint] = Field(default_factory=list)
    drawdown_history: list[dict] = Field(default_factory=list)
    positions: list[PositionPnLHistory] = Field(default_factory=list)


class MTMPnLSnapshot(BaseModel):
    timestamp: datetime
    portfolio_value: float
    cash_balance: float
    position_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    total_pnl_percent: float


class MTMPositionSeries(BaseModel):
    market_id: str
    outcome: str
    market_question: Optional[str] = None
    current_quantity: float
    average_entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    first_trade_at: Optional[datetime] = None
    timestamps: list[datetime] = Field(default_factory=list)
    prices: list[float] = Field(default_factory=list)
    unrealized_pnls: list[float] = Field(default_factory=list)
    total_pnls: list[float] = Field(default_factory=list)


class MarkToMarketResponse(BaseModel):
    portfolio_id: str
    as_of: datetime
    initial_balance: float
    cash_balance: float
    total_value: float
    total_pnl: float
    total_pnl_percent: float
    sharpe_ratio: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_trades: int = 0
    avg_trade_pnl: Optional[float] = None
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None
    pnl_series: list[MTMPnLSnapshot] = Field(default_factory=list)
    positions: list[MTMPositionSeries] = Field(default_factory=list)
