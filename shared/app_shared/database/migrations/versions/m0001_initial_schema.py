"""Initial shared schema migration."""

from app_shared.database.base import Base

version = "0001_initial_schema"


def upgrade(connection) -> None:
    """Create the current shared tables if they do not yet exist."""

    Base.metadata.create_all(bind=connection)
