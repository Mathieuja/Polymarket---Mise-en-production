"""
Database package for SQLAlchemy ORM models and session management.

Exports:
    - Base: SQLAlchemy declarative base for all models
    - engine: SQLAlchemy engine instance
    - SessionLocal: Session factory
    - get_db: FastAPI dependency for database injection
    - init_db: Function to initialize all database tables
    - User: User ORM model
"""

from app.backend.database.database import (
    Base,
    engine,
    SessionLocal,
    get_db,
    init_db,
)
from app.backend.database.models import User

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "User",
]
