"""Public market endpoints backed by PostgreSQL."""

from typing import Any

from app_shared.database import Market, get_db
from app_shared.schemas import MarketSchema, MarketSummarySchema
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/markets", tags=["markets"])


def _summary_id(market: Market) -> str:
    return market.slug or market.external_id


def _market_summary(market: Market) -> dict[str, Any]:
    return {
        "id": _summary_id(market),
        "title": market.question,
        "yes_price": market.yes_price,
        "slug": market.slug,
        "question": market.question,
        "closed": market.closed,
        "active": market.active,
    }


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[MarketSummarySchema],
    summary="List markets from PostgreSQL",
)
def list_markets(
    skip: int = 0,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    markets = (
        db.query(Market)
        .order_by(Market.last_synced_at.desc(), Market.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_market_summary(market) for market in markets]


@router.get(
    "/latest",
    status_code=status.HTTP_200_OK,
    response_model=list[MarketSchema],
    summary="Get latest synced markets",
)
def get_latest_markets(
    limit: int = 1,
    db: Session = Depends(get_db),
):
    """Return the last synced market row(s), newest first."""

    safe_limit = max(1, min(limit, 100))
    markets = (
        db.query(Market)
        .order_by(Market.last_synced_at.desc(), Market.id.desc())
        .limit(safe_limit)
        .all()
    )
    return markets


@router.get(
    "/{market_id}",
    status_code=status.HTTP_200_OK,
    response_model=MarketSchema,
    summary="Get a market by slug or external ID",
)
def get_market(market_id: str, db: Session = Depends(get_db)):
    market = (
        db.query(Market)
        .filter((Market.slug == market_id) | (Market.external_id == market_id))
        .first()
    )

    if market is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market '{market_id}' not found",
        )

    return market
