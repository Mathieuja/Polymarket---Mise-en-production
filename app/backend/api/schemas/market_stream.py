"""Schemas for market stream endpoints backed by Redis."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StreamStartResponse(BaseModel):
    """Response returned when a stream start command is published."""

    status: str = Field(..., description="Status of the stream start")
    asset_id: str = Field(..., description="Asset ID(s) being streamed")
    message: str = Field(..., description="Status message")
    started_by: str = Field(..., description="Initiator identifier")


class StreamStopResponse(BaseModel):
    """Response returned when a stream stop command is published."""

    status: str = Field(..., description="Status of the stream stop")
    message: str = Field(..., description="Status message")
    stopped_by: str = Field(..., description="Initiator identifier")


class TokenOrderbook(BaseModel):
    """Orderbook snapshot for one token."""

    bids: dict[str, float] = Field(
        default_factory=dict,
        description="Bid levels as {price: quantity}",
    )
    asks: dict[str, float] = Field(
        default_factory=dict,
        description="Ask levels as {price: quantity}",
    )


class OrderbookResponse(BaseModel):
    """Response containing the Redis orderbook snapshot."""

    status: str = Field(..., description="Status of the request")
    count: int = Field(..., description="Number of token orderbooks")
    messages: dict[str, TokenOrderbook] = Field(
        default_factory=dict,
        description="Orderbook snapshots by token ID",
    )


class LatestMessageResponse(BaseModel):
    """Response containing the latest message written in Redis stream."""

    status: str = Field(..., description="Status of the request")
    message: dict[str, Any] | None = Field(
        default=None,
        description="Latest message data",
    )
