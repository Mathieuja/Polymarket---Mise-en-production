"""Add hashed password support to users table for secure authentication."""

from sqlalchemy import inspect, text

version = "0006_users_password_hash"


def upgrade(connection) -> None:
    """Add hashed_password column for user credential storage."""

    inspector = inspect(connection)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "hashed_password" in existing_columns:
        return

    connection.execute(
        text(
            'ALTER TABLE "users" '
            'ADD COLUMN IF NOT EXISTS "hashed_password" VARCHAR(255) '
            "NOT NULL DEFAULT 'legacy-no-password'"
        )
    )

    connection.execute(
        text('ALTER TABLE "users" ALTER COLUMN "hashed_password" DROP DEFAULT')
    )
