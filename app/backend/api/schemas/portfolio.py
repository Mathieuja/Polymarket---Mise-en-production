from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    initial_balance: float = Field(default=1000.0, ge=0)
    description: Optional[str] = Field(default=None, max_length=2000)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    initial_balance: float
    cash_balance: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioMetrics(BaseModel):
    portfolio_id: int
    cash_balance: float
    positions_value: float
    total_value: float
    total_pnl: float
    total_pnl_percent: float
    trades_count: int


class MarkToMarketResponse(BaseModel):
    portfolio_id: int
    as_of: datetime
    initial_balance: float
    cash_balance: float
    current_value: float
    pnl: float
    pnl_percent: float
    total_trades: int
    resolution: int


class Position(BaseModel):
    market_id: str
    outcome: str
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float


class PortfolioWithPositions(PortfolioResponse):
    positions: list[Position] = Field(default_factory=list)
    total_value: float
    total_pnl: float
    total_pnl_percent: float
