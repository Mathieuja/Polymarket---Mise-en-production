"""Add persisted portfolio and trade tables."""

from app_shared.database.base import Base
from app_shared.database.models import Portfolio, Trade

version = "m0007_portfolio_trading_tables"


def upgrade(connection) -> None:
    """Create portfolio and trade tables when missing."""

    Base.metadata.create_all(
        bind=connection,
        tables=[Portfolio.__table__, Trade.__table__],
    )