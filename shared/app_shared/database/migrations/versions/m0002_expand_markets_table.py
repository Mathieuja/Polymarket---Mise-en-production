"""Add the full market ingestion columns to the markets table."""

from sqlalchemy import inspect, text

version = "0002_expand_markets_table"


def upgrade(connection) -> None:
    """Add missing columns required by the worker ingestion pipeline."""

    inspector = inspect(connection)
    if "markets" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("markets")}

    columns_to_add = [
        ("slug", 'VARCHAR(255)'),
        ("condition_id", 'VARCHAR(255)'),
        ("description", 'TEXT'),
        ("outcomes", 'JSON'),
        ("outcome_prices", 'JSON'),
        ("clob_token_ids", 'JSON'),
        ("tags", 'JSON'),
        ("rewards", 'JSON'),
        ("raw_payload", 'JSON'),
        ("yes_price", 'DOUBLE PRECISION'),
        ("no_price", 'DOUBLE PRECISION'),
        ("volume_num", 'DOUBLE PRECISION'),
        ("volume_24hr", 'DOUBLE PRECISION'),
        ("volume_7d", 'DOUBLE PRECISION'),
        ("liquidity_num", 'DOUBLE PRECISION'),
        ("best_bid", 'DOUBLE PRECISION'),
        ("best_ask", 'DOUBLE PRECISION'),
        ("spread", 'DOUBLE PRECISION'),
        ("closed", 'BOOLEAN NOT NULL DEFAULT FALSE'),
        ("active", 'BOOLEAN NOT NULL DEFAULT TRUE'),
        ("archived", 'BOOLEAN NOT NULL DEFAULT FALSE'),
        ("end_date_iso", 'VARCHAR(64)'),
        ("start_date_iso", 'VARCHAR(64)'),
        ("source_created_at", 'VARCHAR(64)'),
        ("image", 'VARCHAR(1024)'),
        ("icon", 'VARCHAR(1024)'),
        ("event_slug", 'VARCHAR(255)'),
        ("group_slug", 'VARCHAR(255)'),
        ("first_synced_at", 'TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()'),
        ("last_synced_at", 'TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()'),
        ("created_at", 'TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()'),
        ("updated_at", 'TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()'),
    ]

    for column_name, column_type in columns_to_add:
        if column_name in existing_columns:
            continue
        connection.execute(
            text(
                f'ALTER TABLE "markets" ADD COLUMN IF NOT EXISTS "{column_name}" {column_type}'
            )
        )

    connection.execute(
        text(
            'UPDATE "markets" '
            'SET first_synced_at = COALESCE(first_synced_at, NOW()), '
            'last_synced_at = COALESCE(last_synced_at, NOW()), '
            'created_at = COALESCE(created_at, NOW()), '
            'updated_at = COALESCE(updated_at, NOW())'
        )
    )