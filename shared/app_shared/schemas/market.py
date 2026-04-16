"""
Pydantic schemas for market data validation and API responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MarketCreateSchema(BaseModel):
    """Schema for creating a new market."""

    external_id: str = Field(..., description="Polymarket API market ID")
    question: str = Field(..., description="Market question")
    description: Optional[str] = Field(None, description="Market description")
    end_date: Optional[datetime] = Field(None, description="Market end date")
    is_active: bool = Field(True, description="Whether market is active")


class MarketSchema(MarketCreateSchema):
    """Schema for market API responses."""

    id: int = Field(..., description="Database ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
