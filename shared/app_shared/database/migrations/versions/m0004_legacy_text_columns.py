"""Migrate legacy varchar market columns to TEXT where needed."""

from sqlalchemy import inspect, text

version = "0004_legacy_text_columns"


def upgrade(connection) -> None:
    """Upgrade market string columns that can exceed legacy varchar limits."""

    inspector = inspect(connection)
    if "markets" not in inspector.get_table_names():
        return

    columns = {column["name"]: column for column in inspector.get_columns("markets")}

    # Legacy schema used VARCHAR(500) and VARCHAR(2000); payloads now exceed those.
    for column_name in ("question", "description"):
        column = columns.get(column_name)
        if not column:
            continue

        type_name = column["type"].__class__.__name__.lower()
        if "text" in type_name:
            continue

        connection.execute(
            text(
                f'ALTER TABLE "markets" '
                f'ALTER COLUMN "{column_name}" TYPE TEXT '
                f'USING "{column_name}"::TEXT'
            )
        )
