"""Public market endpoints backed by PostgreSQL.

Endpoints for:
- Listing markets with filters
- Getting market details
- Price history
- Open interest
- Market statistics
"""
from typing import Optional

from app_shared.database import User, get_db
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.backend.api.schemas.market_responses import (
    MarketDetailResponse,
    MarketFilterParams,
    MarketListResponse,
    MarketSummary,
    OpenInterestResponse,
    PriceHistoryResponse,
    SyncStatsResponse,
)
from app.backend.api.dependencies.auth import get_current_active_user_from_query_token
from app.backend.api.services.market_service import MarketService
from app.backend.api.services.polymarket_api import get_polymarket_api

router = APIRouter(
    prefix="/markets",
    tags=["markets"],
)


def get_market_service(db: Session = Depends(get_db)) -> MarketService:
    """Dependency to get MarketService instance."""
    return MarketService(db)


# ==================== List & Filter Endpoints ====================


@router.get(
    "",
    response_model=MarketListResponse,
    summary="List markets with filters",
)
async def list_markets(
    current_user: User = Depends(get_current_active_user_from_query_token),
    market_service: MarketService = Depends(get_market_service),
    # Filter parameters
    search: Optional[str] = Query(None, description="Text search in question/description"),
    closed: Optional[bool] = Query(None, description="Filter by closed status"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    volume_min: Optional[float] = Query(None, ge=0, description="Minimum total volume"),
    volume_max: Optional[float] = Query(None, ge=0, description="Maximum total volume"),
    liquidity_min: Optional[float] = Query(None, ge=0, description="Minimum liquidity"),
    liquidity_max: Optional[float] = Query(None, ge=0, description="Maximum liquidity"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    # Sorting
    sort_by: Optional[str] = Query(
        "volume",
        description="Field to sort by (volume, liquidity, volume_24h)",
    ),
    sort_desc: bool = Query(True, description="Sort descending"),
):
    """
    List markets from database with filtering and pagination.

    Perfect for market explorer:
    - Filter by active/closed status
    - Filter by volume/liquidity ranges
    - Text search across questions
    - Paginated results
    """
    filters = MarketFilterParams(
        search=search,
        closed=closed,
        active=active,
        volume_min=volume_min,
        volume_max=volume_max,
        liquidity_min=liquidity_min,
        liquidity_max=liquidity_max,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )

    _ = current_user

    return await market_service.list_markets(filters)


@router.get(
    "/top",
    response_model=list[MarketSummary],
    summary="Get top markets",
)
async def get_top_markets(
    current_user: User = Depends(get_current_active_user_from_query_token),
    market_service: MarketService = Depends(get_market_service),
    limit: int = Query(20, ge=1, le=100, description="Number of markets"),
    sort_by: str = Query("volume", description="Sort field: volume_24h, volume, liquidity"),
    active_only: bool = Query(True, description="Only active markets"),
):
    """
    Get top markets by volume or liquidity.

    Quick endpoint for dashboard widgets showing top markets.
    """
    _ = current_user

    return await market_service.get_top_markets(
        limit=limit,
        sort_by=sort_by,
        active_only=active_only,
    )


@router.get(
    "/stats",
    response_model=SyncStatsResponse,
    summary="Get sync statistics",
)
async def get_sync_stats(
    current_user: User = Depends(get_current_active_user_from_query_token),
    market_service: MarketService = Depends(get_market_service),
):
    """
    Get market database sync statistics.

    Shows total markets, active/closed counts, and sync timestamps.
    """
    _ = current_user
    stats = await market_service.get_sync_stats()
    return stats


# ==================== Single Market Endpoints ====================

# NOTE: Price history route MUST come before the slug route
# because {slug:path} would otherwise capture "slug/prices" as the slug


@router.get(
    "/by-slug/{slug:path}/prices",
    response_model=PriceHistoryResponse,
    summary="Get price history by slug",
)
async def get_price_history(
    current_user: User = Depends(get_current_active_user_from_query_token),
    slug: str = Path(..., description="Market slug"),
    market_service: MarketService = Depends(get_market_service),
    outcome_index: int = Query(0, ge=0, le=10, description="Outcome index (0=first, 1=second)"),
    start_ts: Optional[int] = Query(None, description="Start Unix timestamp"),
    end_ts: Optional[int] = Query(None, description="End Unix timestamp"),
    force_refresh: bool = Query(False, description="Force fetch from CLOB API"),
):
    """
    Get price history for a market outcome.

    Fetches from CLOB API on demand.

    - **outcome_index**: 0 for first outcome (e.g., "Yes"), 1 for second (e.g., "No")
    - **start_ts/end_ts**: Unix timestamps for time range filter
    """
    _ = current_user

    prices = await market_service.get_price_history(
        slug=slug,
        outcome_index=outcome_index,
        start_ts=start_ts,
        end_ts=end_ts,
        force_refresh=force_refresh,
    )

    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market '{slug}' not found or no price history available",
        )

    return prices


@router.get(
    "/by-slug/{slug:path}",
    response_model=MarketDetailResponse,
    summary="Get market by slug",
)
async def get_market_by_slug(
    current_user: User = Depends(get_current_active_user_from_query_token),
    slug: str = Path(..., description="Market slug"),
    market_service: MarketService = Depends(get_market_service),
    force_refresh: bool = Query(False, description="Force fetch from Polymarket API"),
):
    """
    Get market details by slug.

    Lazy-loads from Polymarket API if not cached.
    Use `force_refresh=true` to always fetch fresh data.
    """
    _ = current_user
    market = await market_service.get_market_by_slug(slug, force_refresh=force_refresh)

    if not market:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market with slug '{slug}' not found",
        )

    return market


@router.get(
    "/by-condition/{condition_id}",
    response_model=MarketDetailResponse,
    summary="Get market by condition ID",
)
async def get_market_by_condition_id(
    current_user: User = Depends(get_current_active_user_from_query_token),
    condition_id: str = Path(..., description="On-chain condition ID"),
    market_service: MarketService = Depends(get_market_service),
    force_refresh: bool = Query(False, description="Force fetch from Polymarket API"),
):
    """
    Get market details by on-chain condition ID.

    Lazy-loads from Polymarket API if not cached.
    """
    _ = current_user
    market = await market_service.get_market_by_condition_id(
        condition_id, force_refresh=force_refresh
    )

    if not market:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market with condition ID '{condition_id}' not found",
        )

    return market


# ==================== Open Interest Endpoints ====================


@router.post(
    "/open-interest",
    response_model=list[OpenInterestResponse],
    summary="Get open interest for markets",
)
async def get_open_interest(
    current_user: User = Depends(get_current_active_user_from_query_token),
    slugs: list[str] = Body(..., description="List of market slugs"),
    market_service: MarketService = Depends(get_market_service),
    force_refresh: bool = Query(False, description="Force fetch from Data API"),
):
    """
    Get open interest for multiple markets.

    POST with list of slugs in request body.
    """
    _ = current_user

    if not slugs:
        return []

    if len(slugs) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 slugs per request",
        )

    return await market_service.get_open_interest(slugs, force_refresh=force_refresh)


@router.post(
    "/admin/refresh",
    response_model=dict,
    summary="Manually trigger market refresh",
)
async def admin_refresh_markets(
    current_user: User = Depends(get_current_active_user_from_query_token),
    market_service: MarketService = Depends(get_market_service),
    limit: int = Query(100, ge=1, le=1000, description="Max markets to sync"),
    active_only: bool = Query(True, description="Only sync active markets"),
):
    """Fetch fresh markets from Gamma API and upsert into PostgreSQL cache."""

    _ = current_user
    api = await get_polymarket_api()

    filters = {}
    if active_only:
        filters["closed"] = False
        filters["active"] = True

    markets = await api.get_all_markets_paginated(
        batch_size=100,
        max_markets=limit,
        **filters,
    )

    count = await market_service.bulk_upsert_markets(markets)

    return {
        "message": f"Refreshed {count} markets",
        "fetched": len(markets),
        "upserted": count,
    }
