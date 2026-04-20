from __future__ import annotations

from app_shared.database import User, get_db
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

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)


@router.get("", response_model=list[PortfolioResponse], summary="List portfolios")
def list_portfolios(
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    return portfolio_service.list_portfolios(current_user.id)


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create portfolio",
)
def create_portfolio(
    body: PortfolioCreate,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    return portfolio_service.create_portfolio(current_user.id, body)


@router.get("/{portfolio_id}", response_model=PortfolioResponse, summary="Get portfolio")
def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = portfolio_service.get_portfolio(portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


@router.patch("/{portfolio_id}", response_model=PortfolioResponse, summary="Update portfolio")
def update_portfolio(
    portfolio_id: int,
    body: PortfolioUpdate,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = portfolio_service.update_portfolio(portfolio_id, current_user.id, body)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete portfolio",
)
def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    if not portfolio_service.delete_portfolio(portfolio_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


@router.post(
    "/{portfolio_id}/trades",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create trade",
)
def add_trade(
    portfolio_id: int,
    body: TradeCreate,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    try:
        trade = portfolio_service.add_trade(portfolio_id, current_user.id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return trade


@router.get("/{portfolio_id}/trades", response_model=TradeHistory, summary="Get trade history")
def get_trades(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    return portfolio_service.get_trades(
        portfolio_id,
        current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{portfolio_id}/metrics",
    response_model=PortfolioMetrics,
    summary="Get portfolio metrics",
)
def get_portfolio_metrics(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    metrics = portfolio_service.calculate_metrics(portfolio_id, current_user.id)
    if metrics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return metrics


@router.get(
    "/{portfolio_id}/mtm",
    response_model=MarkToMarketResponse,
    summary="Get mark-to-market",
)
def get_portfolio_mtm(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    resolution: int = Query(60, ge=1, le=1440),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    mtm = portfolio_service.calculate_mtm(portfolio_id, current_user.id, resolution=resolution)
    if mtm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return mtm


@router.get(
    "/{portfolio_id}/positions",
    response_model=PortfolioWithPositions,
    summary="Get portfolio with positions",
)
def get_portfolio_with_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    portfolio = portfolio_service.get_portfolio_with_positions(portfolio_id, current_user.id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio