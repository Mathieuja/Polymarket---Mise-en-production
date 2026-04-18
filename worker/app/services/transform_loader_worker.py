"""Transform worker: S3 raw JSONL -> DuckDB/Python transform -> PostgreSQL upsert."""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime, timezone

import duckdb
from app_shared.database import IngestionBatch, SessionLocal, init_db
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text

from .logging_utils import configure_worker_logging, short_error
from .market_sync_utils import upsert_markets_batch
from .s3_client import S3RawClient


class TransformWorkerConfig(BaseSettings):
    """Configuration for transform/load stage."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    transform_poll_interval_seconds: int = Field(default=20)
    transform_batch_limit: int = Field(default=5)

    aws_region: str = Field(default="eu-west-3")
    s3_raw_bucket: str = Field(default="")
    s3_raw_prefix: str = Field(default="polymarket/raw")
    s3_endpoint_url: str | None = Field(default=None)
    aws_endpoint: str | None = Field(default=None)

    log_level: str = Field(default="INFO")
    console_log_level: str = Field(default="INFO")
    log_file: str = Field(default="/tmp/polymarket-transform-worker.log")


config = TransformWorkerConfig()


def _resolve_endpoint_url() -> str | None:
    endpoint = config.s3_endpoint_url or config.aws_endpoint
    if not endpoint:
        return None
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


logger = configure_worker_logging(
    logger_name="polymarket_transform_worker",
    log_level=config.log_level,
    console_log_level=config.console_log_level,
    log_file=config.log_file,
)


class TransformLoaderWorker:
    """Loads raw batches from S3, transforms via DuckDB/Python, then upserts PostgreSQL."""

    def __init__(self) -> None:
        if not config.s3_raw_bucket:
            raise ValueError("S3_RAW_BUCKET must be set for transform worker")
        self.running = False
        self.s3 = S3RawClient(
            bucket=config.s3_raw_bucket,
            region=config.aws_region,
            prefix=config.s3_raw_prefix,
            endpoint_url=_resolve_endpoint_url(),
        )

    async def connect(self) -> None:
        init_db()
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        logger.info("Transform worker connected")

    async def disconnect(self) -> None:
        logger.info("Transform worker disconnected")

    def _pull_pending_batches(self) -> list[IngestionBatch]:
        with SessionLocal() as session:
            batches = (
                session.query(IngestionBatch)
                .filter(IngestionBatch.status.in_(["raw_stored", "failed"]))
                .order_by(IngestionBatch.created_at.asc())
                .limit(config.transform_batch_limit)
                .all()
            )
            return batches

    def _mark_processing(self, batch_id: str) -> bool:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            batch = (
                session.query(IngestionBatch)
                .filter(IngestionBatch.batch_id == batch_id)
                .first()
            )
            if batch is None or batch.status == "processing":
                return False
            batch.status = "processing"
            batch.updated_at = now
            session.commit()
            return True

    def _mark_processed(self, batch_id: str, row_count: int) -> None:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            batch = (
                session.query(IngestionBatch)
                .filter(IngestionBatch.batch_id == batch_id)
                .first()
            )
            if batch is None:
                return
            batch.status = "loaded"
            batch.row_count = row_count
            batch.last_error = None
            batch.processed_at = now
            batch.updated_at = now
            session.commit()

    def _mark_failed(self, batch_id: str, error_message: str) -> None:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            batch = (
                session.query(IngestionBatch)
                .filter(IngestionBatch.batch_id == batch_id)
                .first()
            )
            if batch is None:
                return
            batch.status = "failed"
            batch.retry_count += 1
            batch.last_error = error_message
            batch.updated_at = now
            session.commit()

    def _duckdb_read_jsonl(self, rows: list[dict]) -> list[dict]:
        """Pass raw JSONL through DuckDB reader to normalize records."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=True) as tmp:
            for row in rows:
                tmp.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            tmp.flush()

            conn = duckdb.connect(database=":memory:")
            try:
                result = conn.execute(
                    (
                        "SELECT * FROM read_json_auto(?, "
                        "format='newline_delimited', ignore_errors=true)"
                    ),
                    [tmp.name],
                )
                columns = [description[0] for description in result.description]
                data = [dict(zip(columns, record)) for record in result.fetchall()]
                if data:
                    return data
                return rows
            except Exception:
                return rows
            finally:
                conn.close()

    async def _process_batch(self, batch: IngestionBatch) -> None:
        if not self._mark_processing(batch.batch_id):
            return

        try:
            rows = await self.s3.get_jsonl_batch(key=batch.s3_key)
            normalized_rows = self._duckdb_read_jsonl(rows)

            with SessionLocal() as session:
                inserted, updated = upsert_markets_batch(session, normalized_rows)
                session.commit()

            self._mark_processed(batch.batch_id, len(normalized_rows))
            logger.info(
                "Transform batch loaded: batch_id=%s rows=%s inserted=%s updated=%s",
                batch.batch_id,
                len(normalized_rows),
                inserted,
                updated,
            )
        except Exception as exc:
            message = short_error(exc)
            self._mark_failed(batch.batch_id, message)
            logger.error("Transform batch failed: batch_id=%s error=%s", batch.batch_id, message)

    async def run(self) -> None:
        self.running = True
        logger.info("Transform worker loop started")
        while self.running:
            batches = self._pull_pending_batches()
            if not batches:
                await asyncio.sleep(config.transform_poll_interval_seconds)
                continue

            for batch in batches:
                if not self.running:
                    break
                await self._process_batch(batch)

            await asyncio.sleep(0.1)

    def stop(self) -> None:
        self.running = False


async def main() -> None:
    worker = TransformLoaderWorker()
    try:
        await worker.connect()
        await worker.run()
    except Exception as exc:
        logger.error("Transform worker failed: %s", short_error(exc))
        raise
    finally:
        await worker.disconnect()
