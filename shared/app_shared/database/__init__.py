"""
Database package for SQLAlchemy ORM models and session management.

Exports:
    - Base: SQLAlchemy declarative base for all models
    - engine: SQLAlchemy engine instance
    - SessionLocal: Session factory
    - get_db: FastAPI dependency for database injection
    - init_db: Function to initialize all database tables
    - User, Market, MarketSyncState, IngestionBatch: ORM models
"""

from app_shared.database.base import Base
from app_shared.database.database import SessionLocal, engine, get_db, init_db
from app_shared.database.models import IngestionBatch, Market, MarketSyncState, User

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "User",
    "Market",
    "MarketSyncState",
    "IngestionBatch",
]
