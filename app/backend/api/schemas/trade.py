from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeCreate(BaseModel):
    market_id: str = Field(..., min_length=1, max_length=255)
    outcome: str = Field(..., min_length=1, max_length=255)
    side: TradeSide
    quantity: float = Field(..., gt=0)
    price: float = Field(..., ge=0, le=1)
    trade_timestamp: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)


class TradeResponse(BaseModel):
    id: str
    portfolio_id: str
    market_id: str
    outcome: str
    side: str
    quantity: float
    price: float
    total_value: float
    trade_timestamp: datetime
    created_at: datetime
    notes: Optional[str] = None
    market_question: Optional[str] = None


class TradeHistory(BaseModel):
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
