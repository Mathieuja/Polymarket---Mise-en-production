"""
Database connection and session management for SQLAlchemy.

This module handles:
- SQLAlchemy engine creation from DATABASE_URL environment variable
- Base class for all ORM models
- Session factory and dependency injection for FastAPI
"""

from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Get database URL from environment variable
# Format: postgresql://user:password@host:port/database
DATABASE_URL = getenv(
    "DATABASE_URL",
    "postgresql+psycopg://polymarket_user:polymarket_password@db:5432/polymarket_db",
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All models should inherit from this class to use the declarative ORM system.
    """

    pass


# Create SQLAlchemy engine
# pool_pre_ping=True: verifies connections are alive before using them
# echo=False: set to True for SQL query logging during development
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Session factory for creating new database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Session:
    """
    FastAPI dependency to inject database session into route handlers.

    Usage:
        from fastapi import Depends
        from app.backend.database.database import get_db

        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Session: A SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.

    This should be called during application startup to create all tables
    defined by the ORM models (if they don't already exist).
    """
    Base.metadata.create_all(bind=engine)
