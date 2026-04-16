"""
SQLAlchemy declarative base for all ORM models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All models should inherit from this class to use the declarative ORM system.
    """

    pass
