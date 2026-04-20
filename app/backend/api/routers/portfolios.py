from __future__ import annotations

from datetime import datetime
from typing import Optional

from app_shared.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.backend.api.dependencies.auth import get_current_active_user
from app.backend.api.schemas.portfolio import (
    MarkToMarketResponse,
    PortfolioCreate,
    PortfolioMetrics,
    PortfolioResponse,
    PortfolioUpdate,
    PortfolioWithPositions,
)
from app.backend.api.schemas.trade import TradeCreate, TradeHistory, TradeResponse
from app.backend.api.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)


@router.get("", response_model=list[PortfolioResponse], summary="List portfolios")
async def list_portfolios(
    current_user=Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    return await portfolio_service.list_portfolios(current_user.id)


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create portfolio",
)
async def create_portfolio(
    body: PortfolioCreate,
    current_user=Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    return await portfolio_service.create_portfolio(current_user.id, body)


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioWithPositions,
    summary="Get portfolio with positions",
)
async def get_portfolio(
    portfolio_id: int,
    current_user=Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = await portfolio_service.get_portfolio_with_positions(portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


@router.patch("/{portfolio_id}", response_model=PortfolioResponse, summary="Update portfolio")
async def update_portfolio(
    portfolio_id: int,
    body: PortfolioUpdate,
    current_user=Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = await portfolio_service.update_portfolio(portfolio_id, current_user.id, body)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete portfolio")
async def delete_portfolio(
    portfolio_id: int,
    current_user=Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    deleted = await portfolio_service.delete_portfolio(portfolio_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


@router.post(
    "/{portfolio_id}/trades",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add trade to portfolio",
)
async def add_trade(
    portfolio_id: int,
    body: TradeCreate,
    current_user=Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    trade = await portfolio_service.add_trade(portfolio_id, current_user.id, body)
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return trade


@router.get("/{portfolio_id}/trades", response_model=TradeHistory, summary="Get trade history")
async def get_trades(
    portfolio_id: int,
    current_user=Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    return await portfolio_service.get_trades(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/{portfolio_id}/metrics",
    response_model=PortfolioMetrics,
    summary="Calculate portfolio metrics",
)
async def get_portfolio_metrics(
    portfolio_id: int,
    current_user=Depends(get_current_active_user),
    as_of: Optional[datetime] = Query(None),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    metrics = await portfolio_service.calculate_metrics(portfolio_id, current_user.id, as_of)
    if metrics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return metrics


@router.get(
    "/{portfolio_id}/mtm",
    response_model=MarkToMarketResponse,
    summary="Get mark-to-market P&L",
)
async def get_mark_to_market(
    portfolio_id: int,
    current_user=Depends(get_current_active_user),
    resolution: int = Query(60, ge=1, le=1440),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    result = await portfolio_service.mark_to_market(
        portfolio_id,
        current_user.id,
        resolution_minutes=resolution,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return result
