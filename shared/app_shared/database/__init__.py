"""
Database package for SQLAlchemy ORM models and session management.

Exports:
    - Base: SQLAlchemy declarative base for all models
    - engine: SQLAlchemy engine instance
    - SessionLocal: Session factory
    - get_db: FastAPI dependency for database injection
    - init_db: Function to initialize all database tables
    - User, Market: ORM models
"""

from app_shared.database.base import Base
from app_shared.database.database import engine, get_db, init_db, SessionLocal
from app_shared.database.models import Market, User

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "User",
    "Market",
]
