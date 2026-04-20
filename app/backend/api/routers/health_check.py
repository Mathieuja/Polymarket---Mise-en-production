"""
Health check endpoint.
"""

from fastapi import APIRouter, status

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