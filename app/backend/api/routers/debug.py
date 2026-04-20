"""
Debug and monitoring endpoints for development and pipeline verification.

These endpoints help verify:
- Database connection health
- Ingestion pipeline status
- Latest batch information
"""

import json
import os

import boto3
from app_shared.database import IngestionBatch, Market, User, get_db
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.backend.api.dependencies.auth import get_current_active_user

router = APIRouter(
    prefix="/debug",
    tags=["debug"],
    dependencies=[Depends(get_current_active_user)],
)


def _resolve_s3_endpoint() -> str | None:
    endpoint = os.getenv("S3_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT")
    if not endpoint:
        return None
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


def _s3_client():
    region = os.getenv("AWS_REGION", "eu-west-3")
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=_resolve_s3_endpoint(),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _read_jsonl_rows(bucket: str, key: str, limit: int) -> list[dict]:
    response = _s3_client().get_object(Bucket=bucket, Key=key)
    payload = response["Body"].read().decode("utf-8")
    rows: list[dict] = []
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
        if len(rows) >= limit:
            break
    return rows


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Test database connection",
)
def health(db: Session = Depends(get_db)):
    """
    Test the database connection and return pipeline stats.

    Returns:
        dict: Status and count of key entities
    """
    try:
        user_count = db.query(User).count()
        market_count = db.query(Market).count()
        return {
            "status": "ok",
            "message": "Database connection successful",
            "user_count": user_count,
            "market_count": market_count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}",
        )


@router.get(
    "/latest-increment",
    status_code=status.HTTP_200_OK,
    summary="Get latest auto-increment IDs",
)
def latest_increment(db: Session = Depends(get_db)):
    """
    Return the latest auto-increment IDs for key pipeline tables.

    Useful for verifying that the ingestion pipeline is advancing.
    """
    try:
        latest_market = db.query(Market).order_by(Market.id.desc()).first()
        latest_batch = db.query(IngestionBatch).order_by(IngestionBatch.id.desc()).first()

        return {
            "status": "ok",
            "latest_market_id": latest_market.id if latest_market else None,
            "latest_ingestion_batch_id": latest_batch.id if latest_batch else None,
            "latest_ingestion_batch_status": latest_batch.status if latest_batch else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read latest increment: {str(e)}",
        )


@router.get(
    "/latest-full",
    status_code=status.HTTP_200_OK,
    summary="Get latest full batch",
)
def latest_full_batch(db: Session = Depends(get_db)):
    """
    Return the latest ingestion batch with sync_type='full'.

    Useful for monitoring full sync progress.
    """
    try:
        batch = (
            db.query(IngestionBatch)
            .filter(IngestionBatch.sync_type == "full")
            .order_by(IngestionBatch.id.desc())
            .first()
        )

        if batch is None:
            return {
                "status": "ok",
                "message": "No full batch found",
                "latest_full": None,
            }

        return {
            "status": "ok",
            "latest_full": {
                "id": batch.id,
                "batch_id": batch.batch_id,
                "sync_type": batch.sync_type,
                "status": batch.status,
                "row_count": batch.row_count,
                "s3_bucket": batch.s3_bucket,
                "s3_key": batch.s3_key,
                "created_at": batch.created_at,
                "updated_at": batch.updated_at,
                "processed_at": batch.processed_at,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read latest full batch: {str(e)}",
        )


@router.get(
    "/latest-raw/{sync_type}",
    status_code=status.HTTP_200_OK,
    summary="Read latest raw markets from S3",
)
def latest_raw_markets(sync_type: str, limit: int = 1, db: Session = Depends(get_db)):
    """
    Return latest raw market payload rows from the latest S3 batch.

    Useful for debugging the raw data before transformation.

    Args:
        sync_type: "full" or "incremental"
        limit: Number of rows to return (max 100)
    """
    sync_type = sync_type.strip().lower()
    if sync_type not in {"full", "incremental"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sync_type must be one of: full, incremental",
        )

    safe_limit = max(1, min(limit, 100))

    try:
        batch = (
            db.query(IngestionBatch)
            .filter(IngestionBatch.sync_type == sync_type)
            .order_by(IngestionBatch.id.desc())
            .first()
        )

        if batch is None:
            return {
                "status": "ok",
                "message": f"No {sync_type} batch found",
                "sync_type": sync_type,
                "batch": None,
                "markets": [],
            }

        rows = _read_jsonl_rows(batch.s3_bucket, batch.s3_key, safe_limit)
        return {
            "status": "ok",
            "sync_type": sync_type,
            "batch": {
                "id": batch.id,
                "batch_id": batch.batch_id,
                "s3_bucket": batch.s3_bucket,
                "s3_key": batch.s3_key,
                "row_count": batch.row_count,
                "status": batch.status,
                "created_at": batch.created_at,
                "processed_at": batch.processed_at,
            },
            "markets": rows,
            "returned_count": len(rows),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read latest raw data for {sync_type}: {str(e)}",
        )


@router.get(
    "/latest-raw-full",
    status_code=status.HTTP_200_OK,
    summary="Get latest raw full batch",
)
def latest_raw_full_markets(limit: int = 1, db: Session = Depends(get_db)):
    """Shortcut endpoint for latest raw full batch."""
    return latest_raw_markets(sync_type="full", limit=limit, db=db)


@router.get(
    "/latest-raw-incremental",
    status_code=status.HTTP_200_OK,
    summary="Get latest raw incremental batch",
)
def latest_raw_incremental_markets(limit: int = 1, db: Session = Depends(get_db)):
    """Shortcut endpoint for latest raw incremental batch."""
    return latest_raw_markets(sync_type="incremental", limit=limit, db=db)
