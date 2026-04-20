"""Ensure legacy markets.is_active is compatible with current inserts."""

from sqlalchemy import inspect, text

version = "0003_legacy_is_active_compat"


def upgrade(connection) -> None:
    """Patch legacy schemas that still have the old non-null is_active column."""

    inspector = inspect(connection)
    if "markets" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("markets")}
    if "is_active" not in columns:
        return

    # Make inserts that don't provide is_active fall back to TRUE.
    connection.execute(
        text('ALTER TABLE "markets" ALTER COLUMN "is_active" SET DEFAULT TRUE')
    )

    if "active" in columns:
        connection.execute(
            text(
                'UPDATE "markets" '
                'SET "is_active" = COALESCE("is_active", "active", TRUE) '
                'WHERE "is_active" IS NULL'
            )
        )
    else:
        connection.execute(
            text(
                'UPDATE "markets" '
                'SET "is_active" = TRUE '
                'WHERE "is_active" IS NULL'
            )
        )
