"""SQLAlchemy ORM models for Polymarket backend and worker."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app_shared.database.base import Base


class User(Base):
    """User model for the existing demo authentication flow."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Market(Base):
    """Polymarket market record stored in PostgreSQL."""

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    external_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    slug: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    condition_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    outcomes: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    outcome_prices: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    clob_token_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    rewards: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    yes_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    no_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_24hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_7d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liquidity_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_ask: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    end_date_iso: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    start_date_iso: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_created_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    event_slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group_slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    first_synced_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        question_short = self.question[:50]
        return (
            f"<Market(id={self.id}, external_id={self.external_id}, "
            f"question={question_short})>"
        )


class MarketSyncState(Base):
    """Persisted worker sync state for resumable market ingestion."""

    __tablename__ = "market_sync_states"

    sync_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class IngestionBatch(Base):
    """Tracks S3 raw batches through transform and PostgreSQL load stages."""

    __tablename__ = "ingestion_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )
    sync_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="raw_stored", index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
