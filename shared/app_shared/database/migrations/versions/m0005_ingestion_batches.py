"""Create ingestion batch checkpoint table for S3->DuckDB->PostgreSQL pipeline."""

from sqlalchemy import inspect, text

version = "0005_ingestion_batches"


def upgrade(connection) -> None:
    """Create ingestion_batches table and supporting indexes if absent."""

    inspector = inspect(connection)
    if "ingestion_batches" in inspector.get_table_names():
        return

    # Previous interrupted attempts can leave an orphan sequence without a table.
    # Drop it to make table creation idempotent and recoverable.
    connection.execute(text('DROP SEQUENCE IF EXISTS "ingestion_batches_id_seq"'))

    connection.execute(
        text(
            'CREATE TABLE "ingestion_batches" ('
            'id SERIAL PRIMARY KEY, '
            'batch_id VARCHAR(200) NOT NULL UNIQUE, '
            'sync_type VARCHAR(40) NOT NULL, '
            's3_bucket VARCHAR(255) NOT NULL, '
            's3_key VARCHAR(1024) NOT NULL, '
            'row_count INTEGER NOT NULL DEFAULT 0, '
            "status VARCHAR(40) NOT NULL DEFAULT 'raw_stored', "
            'retry_count INTEGER NOT NULL DEFAULT 0, '
            'last_error TEXT NULL, '
            'created_at TIMESTAMP NOT NULL DEFAULT NOW(), '
            'updated_at TIMESTAMP NOT NULL DEFAULT NOW(), '
            'processed_at TIMESTAMP NULL'
            ')'
        )
    )

    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_ingestion_batches_status" '
            'ON "ingestion_batches" ("status")'
        )
    )
    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_ingestion_batches_batch_id" '
            'ON "ingestion_batches" ("batch_id")'
        )
    )
    connection.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "ix_ingestion_batches_s3_key" '
            'ON "ingestion_batches" ("s3_key")'
        )
    )
