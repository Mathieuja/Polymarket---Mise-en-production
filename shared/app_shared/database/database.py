"""Database connection and session management for SQLAlchemy."""

from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app_shared.database.migrations import run_migrations

# Get database URL from environment variable
# Format: postgresql+psycopg://user:password@host:port/database
DATABASE_URL = getenv(
    "DATABASE_URL",
    "postgresql+psycopg://polymarket_user:polymarket_password@db:5432/polymarket_db",
)


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
        from app_shared.database import get_db

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
    Initialize database schema through versioned migrations.

    The project uses a lightweight migration runner stored in
    ``app_shared.database.migrations`` so schema changes stay versioned and can
    be applied to existing PostgreSQL volumes without manual intervention.
    """
    run_migrations(engine)
