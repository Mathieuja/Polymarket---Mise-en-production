"""Market stream endpoints powered by Redis and live_data_worker."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

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
    dependencies=[Depends(get_current_active_user_from_query_token)],
)


@router.post(
    "/start/{asset_id}",
    summary="Start live data stream",
    response_model=StreamStartResponse,
)
async def start_stream(asset_id: str) -> StreamStartResponse:
    """Start streaming live data for one or more comma-separated assets."""

    try:
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
async def stop_stream() -> StreamStopResponse:
    """Stop live data streaming and clear live worker cache."""

    try:
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
async def get_messages() -> OrderbookResponse:
    """Return current orderbook snapshot from Redis JSON."""

    try:
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
async def get_latest_message() -> LatestMessageResponse:
    """Return latest entry from Redis stream."""

    try:
        message = MarketStreamService().get_latest_message()
        if message is None:
            return LatestMessageResponse(status="no_data", message=None)

        return LatestMessageResponse(status="ok", message=message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
