"""
SQLAlchemy ORM models for Polymarket backend and worker.

This module defines database models using SQLAlchemy 2.0 syntax with type hints.
Models are shared between backend and worker to ensure consistency.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app_shared.database.base import Base


class User(Base):
    """
    User model for basic user management.

    Attributes:
        id: Unique identifier for the user (primary key)
        name: User's display name
        email: User's email address (unique)
        created_at: Timestamp when user was created
    """

    __tablename__ = "users"

    # Primary key with auto-increment
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User name as string
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Email address (unique constraint for email lookups)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        """String representation of User instance."""
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Market(Base):
    """
    Market model for Polymarket trading data.

    This model stores information about prediction markets fetched from Polymarket API.
    Used by both backend (API endpoints) and worker (data ingestion).

    Attributes:
        id: Unique identifier for the market (primary key)
        external_id: Polymarket API market ID (unique)
        question: Market question/title
        description: Detailed market description
        end_date: When the market closes
        is_active: Whether the market is currently active
        created_at: Timestamp when record was created in DB
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "markets"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # External market ID from Polymarket API
    external_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Market question
    question: Mapped[str] = mapped_column(String(500), nullable=False)

    # Market description
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # Market end date
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Is market active
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timestamps
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
        """String representation of Market instance."""
        question_short = self.question[:50]
        return f"<Market(id={self.id}, external_id={self.external_id}, question={question_short})>"
