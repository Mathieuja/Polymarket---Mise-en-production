"""
Health check endpoint.
"""

import os

from app_shared.database import get_db
from fastapi import APIRouter, status
from sqlalchemy import text

from app.backend.api.services.market_stream_service import MarketStreamService

router = APIRouter(prefix="/health", tags=["health"])

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Ping the API to check if it's alive",
)
async def health_check():
    """
    Health check endpoint to verify that the API is running.
    """
    return {"status": "ok"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check with dependencies",
)
async def readiness_check():
    """Verify primary runtime dependencies (PostgreSQL and Redis)."""

    checks = {
        "api": "healthy",
        "postgres": "unknown",
        "redis": "unknown",
    }

    db = next(get_db())
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "healthy"
    except Exception as exc:
        checks["postgres"] = f"unhealthy: {str(exc)}"
    finally:
        db.close()

    try:
        service = MarketStreamService()
        service._redis.ping()
        checks["redis"] = "healthy"
    except Exception as exc:
        checks["redis"] = f"unhealthy: {str(exc)}"

    all_healthy = all(value == "healthy" for value in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "redis_host": os.getenv("REDIS_HOST", "redis"),
    }