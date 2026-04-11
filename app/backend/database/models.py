"""
SQLAlchemy ORM models for the Polymarket backend.

This module defines database models using SQLAlchemy 2.0 syntax with type hints.
"""

from typing import Optional

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.backend.database.database import Base


class User(Base):
    """
    User model for basic user management.

    Attributes:
        id: Unique identifier for the user (primary key)
        name: User's display name
        email: User's email address (unique)
    """

    __tablename__ = "users"

    # Primary key with auto-increment
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User name as string
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Email address (unique constraint for email lookups)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:
        """String representation of User instance."""
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
