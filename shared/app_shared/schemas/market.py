"""Pydantic schemas for market data validation and API responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MarketSummarySchema(BaseModel):
    """Lightweight market payload used by the public /markets endpoint."""

    id: str = Field(..., description="Stable market identifier")
    title: str = Field(..., description="Market title")
    yes_price: Optional[float] = Field(None, description="YES price if available")
    slug: Optional[str] = Field(None, description="Polymarket slug")
    question: Optional[str] = Field(None, description="Original market question")
    closed: bool = Field(False, description="Whether the market is closed")
    active: bool = Field(True, description="Whether the market is active")

    class Config:
        from_attributes = True


class MarketCreateSchema(BaseModel):
    """Schema for creating or seeding a market row."""

    external_id: str = Field(..., description="Polymarket API market ID")
    slug: Optional[str] = Field(None, description="Polymarket slug")
    condition_id: Optional[str] = Field(None, description="Condition ID")
    question: str = Field(..., description="Market question")
    description: Optional[str] = Field(None, description="Market description")
    outcomes: list[str] = Field(default_factory=list)
    outcome_prices: list[float] = Field(default_factory=list)
    clob_token_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rewards: dict = Field(default_factory=dict)
    raw_payload: dict = Field(default_factory=dict)
    yes_price: Optional[float] = Field(None, description="YES price")
    no_price: Optional[float] = Field(None, description="NO price")
    volume_num: Optional[float] = Field(None, description="Total volume")
    volume_24hr: Optional[float] = Field(None, description="24h volume")
    volume_7d: Optional[float] = Field(None, description="7d volume")
    liquidity_num: Optional[float] = Field(None, description="Liquidity")
    best_bid: Optional[float] = Field(None, description="Best bid")
    best_ask: Optional[float] = Field(None, description="Best ask")
    spread: Optional[float] = Field(None, description="Spread")
    closed: bool = Field(False, description="Whether the market is closed")
    active: bool = Field(True, description="Whether the market is active")
    archived: bool = Field(False, description="Whether the market is archived")
    end_date_iso: Optional[str] = Field(None, description="ISO end date")
    start_date_iso: Optional[str] = Field(None, description="ISO start date")
    source_created_at: Optional[str] = Field(None, description="Source creation date")
    image: Optional[str] = Field(None, description="Image URL")
    icon: Optional[str] = Field(None, description="Icon URL")
    event_slug: Optional[str] = Field(None, description="Event slug")
    group_slug: Optional[str] = Field(None, description="Group slug")


class MarketSchema(MarketCreateSchema):
    """Full market schema for backend read endpoints."""

    id: int = Field(..., description="Database ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    first_synced_at: datetime = Field(..., description="First time this row was synced")
    last_synced_at: datetime = Field(..., description="Last sync timestamp")

    class Config:
        from_attributes = True
