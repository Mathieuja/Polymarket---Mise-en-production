from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TradeCreate(BaseModel):
    market_id: str = Field(min_length=1, max_length=255)
    outcome: str = Field(min_length=1, max_length=255)
    side: str = Field(min_length=3, max_length=4)
    quantity: float = Field(gt=0)
    price: float = Field(ge=0, le=1)
    notes: Optional[str] = Field(default=None, max_length=4000)


class TradeResponse(BaseModel):
    id: int
    portfolio_id: int
    market_id: str
    outcome: str
    side: str
    quantity: float
    price: float
    trade_timestamp: datetime
    created_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class TradeHistory(BaseModel):
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int
    has_more: bool