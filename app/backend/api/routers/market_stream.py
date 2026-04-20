"""Market stream endpoints powered by Redis and live_data_worker."""

from __future__ import annotations

from app_shared.database import User
from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.backend.api.dependencies.auth import get_current_active_user_from_query_token
from app.backend.api.schemas.market_stream import (
    LatestMessageResponse,
    OrderbookResponse,
    StreamStartResponse,
    StreamStopResponse,
)
from app.backend.api.services.market_stream_service import MarketStreamService

router = APIRouter(
    prefix="/market-stream",
    tags=["Market Stream"],
)


@router.post(
    "/start/{asset_id}",
    summary="Start live data stream",
    response_model=StreamStartResponse,
)
async def start_stream(
    current_user: User = Depends(get_current_active_user_from_query_token),
    asset_id: str = Path(..., description="One or more comma-separated asset ids"),
) -> StreamStartResponse:
    """Start streaming live data for one or more comma-separated assets."""

    try:
        _ = current_user
        asset_ids = [value.strip() for value in asset_id.split(",") if value.strip()]
        if not asset_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one asset_id must be provided",
            )

        MarketStreamService().start_stream(asset_ids)
        return StreamStartResponse(
            status="started",
            asset_id=asset_id,
            message=f"Streaming started for asset {asset_id}",
            started_by="system",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/stop",
    summary="Stop live data stream",
    response_model=StreamStopResponse,
)
async def stop_stream(
    current_user: User = Depends(get_current_active_user_from_query_token),
) -> StreamStopResponse:
    """Stop live data streaming and clear live worker cache."""

    try:
        _ = current_user
        MarketStreamService().stop_stream()
        return StreamStopResponse(
            status="stopped",
            message="Stop command sent and data cleared",
            stopped_by="system",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/orderbook",
    summary="Get all streamed messages",
    response_model=OrderbookResponse,
)
async def get_messages(
    current_user: User = Depends(get_current_active_user_from_query_token),
) -> OrderbookResponse:
    """Return current orderbook snapshot from Redis JSON."""

    try:
        _ = current_user
        messages = MarketStreamService().get_orderbook_snapshot()
        return OrderbookResponse(
            status="ok",
            count=len(messages),
            messages=messages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/latest",
    summary="Get latest streamed message",
    response_model=LatestMessageResponse,
)
async def get_latest_message(
    current_user: User = Depends(get_current_active_user_from_query_token),
) -> LatestMessageResponse:
    """Return latest entry from Redis stream."""

    try:
        _ = current_user
        message = MarketStreamService().get_latest_message()
        if message is None:
            return LatestMessageResponse(status="no_data", message=None)

        return LatestMessageResponse(status="ok", message=message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
