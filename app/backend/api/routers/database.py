"""
Database test endpoints for development and verification.

These endpoints verify that the database connection is working correctly.
"""

import json
import os

import boto3
from app_shared.database import IngestionBatch, Market, User, get_db
from app_shared.schemas import MarketCreateSchema, MarketSchema
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/db", tags=["database"])


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
    "/latest-increment",
    status_code=status.HTTP_200_OK,
    summary="Read latest database increments",
)
def latest_increment(db: Session = Depends(get_db)):
    """Return the latest auto-increment IDs for key pipeline tables."""

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
    summary="Read latest full batch added",
)
def latest_full_batch(db: Session = Depends(get_db)):
    """Return the latest ingestion batch with sync_type='full'."""

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
    summary="Read latest raw markets from S3 by sync type",
)
def latest_raw_markets(sync_type: str, limit: int = 1, db: Session = Depends(get_db)):
    """Return latest raw market payload rows from the latest S3 batch."""

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
    summary="Read latest raw full markets from S3",
)
def latest_raw_full_markets(limit: int = 1, db: Session = Depends(get_db)):
    """Shortcut endpoint for latest raw full batch."""

    return latest_raw_markets(sync_type="full", limit=limit, db=db)


@router.get(
    "/latest-raw-incremental",
    status_code=status.HTTP_200_OK,
    summary="Read latest raw incremental markets from S3",
)
def latest_raw_incremental_markets(limit: int = 1, db: Session = Depends(get_db)):
    """Shortcut endpoint for latest raw incremental batch."""

    return latest_raw_markets(sync_type="incremental", limit=limit, db=db)


@router.get(
    "/test",
    status_code=status.HTTP_200_OK,
    summary="Test database connection",
)
def test_db_connection(db: Session = Depends(get_db)):
    """
    Test the database connection by attempting a simple query.

    Returns:
        dict: Status message and user count
    """
    try:
        # Simple query to verify database connection
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


@router.post(
    "/test-create-user",
    status_code=status.HTTP_201_CREATED,
    summary="Create a test user",
)
def create_test_user(
    name: str = "Test User",
    email: str = "test@example.com",
    db: Session = Depends(get_db),
):
    """
    Create a test user in the database.

    Args:
        name: User's name
        email: User's email address

    Returns:
        dict: Created user information
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{email}' already exists.",
            )

        # Create new user
        user = User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "status": "created",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get("/markets", response_model=list[MarketSchema], summary="List all markets")
def list_markets(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    List all markets from the database.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        list: List of markets
    """
    try:
        markets = db.query(Market).offset(skip).limit(limit).all()
        return markets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/markets",
    response_model=MarketSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a market",
)
def create_market(market: MarketCreateSchema, db: Session = Depends(get_db)):
    """
    Create a new market in the database.

    Args:
        market: Market data

    Returns:
        Market: Created market with ID and timestamps
    """
    try:
        db_market = Market(**market.model_dump())
        db.add(db_market)
        db.commit()
        db.refresh(db_market)
        return db_market
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Market with external_id '{market.external_id}' already exists.",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create market: {str(e)}",
        )
