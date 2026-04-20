"""Create portfolios and trades tables for paper-trading endpoints."""

from sqlalchemy import inspect, text

version = "0007_portfolios_and_trades"


def upgrade(connection) -> None:
    """Create portfolio/trade tables and indexes if they do not exist."""

    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())

    if "portfolios" not in existing_tables:
        connection.execute(
            text(
                'CREATE TABLE "portfolios" ('
                'id SERIAL PRIMARY KEY, '
                'user_id INTEGER NOT NULL, '
                'name VARCHAR(100) NOT NULL, '
                'description TEXT NULL, '
                'initial_balance FLOAT NOT NULL DEFAULT 10000.0, '
                'is_active BOOLEAN NOT NULL DEFAULT TRUE, '
                'created_at TIMESTAMP NOT NULL DEFAULT NOW()'
                ')'
            )
        )

    if "trades" not in existing_tables:
        connection.execute(
            text(
                'CREATE TABLE "trades" ('
                'id SERIAL PRIMARY KEY, '
                'portfolio_id INTEGER NOT NULL, '
                'market_id VARCHAR(255) NOT NULL, '
                'outcome VARCHAR(255) NOT NULL, '
                'side VARCHAR(10) NOT NULL, '
                'quantity FLOAT NOT NULL, '
                'price FLOAT NOT NULL, '
                'trade_timestamp TIMESTAMP NOT NULL DEFAULT NOW(), '
                'created_at TIMESTAMP NOT NULL DEFAULT NOW(), '
                'notes TEXT NULL'
                ')'
            )
        )

    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_portfolios_user_id" '
            'ON "portfolios" ("user_id")'
        )
    )
    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_trades_portfolio_id" '
            'ON "trades" ("portfolio_id")'
        )
    )
    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_trades_market_id" '
            'ON "trades" ("market_id")'
        )
    )
    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_trades_trade_timestamp" '
            'ON "trades" ("trade_timestamp")'
        )
    )
