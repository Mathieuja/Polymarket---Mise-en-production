"""Raw ingestion worker: Gamma API -> S3 raw JSONL -> ingestion checkpoint table."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from app_shared.database import IngestionBatch, MarketSyncState, SessionLocal, init_db
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text

from .logging_utils import configure_worker_logging, short_error
from .market_sync_utils import GammaAPIClient
from .s3_client import S3RawClient


class RawWorkerConfig(BaseSettings):
    """Configuration for raw ingestion stage."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sync_interval_minutes: int = Field(default=30)
    full_sync_interval_hours: int = Field(default=24)
    batch_size: int = Field(default=200)
    gamma_api_url: str = Field(default="https://gamma-api.polymarket.com")
    request_timeout_seconds: float = Field(default=60.0)

    aws_region: str = Field(default="eu-west-3")
    s3_raw_bucket: str = Field(default="")
    s3_raw_prefix: str = Field(default="polymarket/raw")
    s3_endpoint_url: Optional[str] = Field(default=None)
    aws_endpoint: Optional[str] = Field(default=None)

    log_level: str = Field(default="INFO")
    console_log_level: str = Field(default="INFO")
    log_file: str = Field(default="/tmp/polymarket-raw-worker.log")


config = RawWorkerConfig()


def _resolve_endpoint_url() -> Optional[str]:
    endpoint = config.s3_endpoint_url or config.aws_endpoint
    if not endpoint:
        return None
    endpoint = endpoint.strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


logger = configure_worker_logging(
    logger_name="polymarket_raw_worker",
    log_level=config.log_level,
    console_log_level=config.console_log_level,
    log_file=config.log_file,
)


class RawIngestionWorker:
    """Collects Polymarket raw batches and writes them to S3."""

    def __init__(self) -> None:
        self.running = False
        self.api = GammaAPIClient(
            base_url=config.gamma_api_url,
            timeout_seconds=config.request_timeout_seconds,
        )
        if not config.s3_raw_bucket:
            raise ValueError("S3_RAW_BUCKET must be set for raw ingestion worker")
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
        logger.info("Raw worker connected to PostgreSQL and S3 bucket %s", config.s3_raw_bucket)

    async def disconnect(self) -> None:
        await self.api.close()
        logger.info("Raw worker disconnected")

    def _get_sync_state(self, sync_id: str) -> Optional[MarketSyncState]:
        with SessionLocal() as session:
            return session.get(MarketSyncState, sync_id)

    def _save_sync_state(
        self,
        *,
        sync_id: str,
        offset: int,
        total_fetched: int,
        is_complete: bool,
        filters: dict[str, Any],
        last_error: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            state = session.get(MarketSyncState, sync_id)
            if state is None:
                state = MarketSyncState(sync_id=sync_id, started_at=now)
                session.add(state)

            state.offset = offset
            state.total_fetched = total_fetched
            state.total_inserted = 0
            state.total_updated = 0
            state.is_complete = is_complete
            state.filters = filters
            state.last_error = last_error
            state.updated_at = now
            session.commit()

    def _record_batch(self, *, batch_id: str, sync_type: str, s3_key: str, row_count: int) -> None:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            existing = session.query(IngestionBatch).filter(IngestionBatch.batch_id == batch_id).first()
            if existing is not None:
                return

            session.add(
                IngestionBatch(
                    batch_id=batch_id,
                    sync_type=sync_type,
                    s3_bucket=config.s3_raw_bucket,
                    s3_key=s3_key,
                    row_count=row_count,
                    status="raw_stored",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def _clear_state(self, sync_id: str) -> None:
        with SessionLocal() as session:
            state = session.get(MarketSyncState, sync_id)
            if state is not None:
                session.delete(state)
                session.commit()

    def _last_full_sync(self) -> Optional[datetime]:
        with SessionLocal() as session:
            state = session.get(MarketSyncState, "raw_full_sync")
            if state and state.is_complete:
                return state.updated_at
        return None

    async def _sync(self, *, sync_id: str, sync_type: str, filters: dict[str, Any]) -> dict[str, Any]:
        offset = 0
        total_fetched = 0
        start = datetime.now(timezone.utc)
        logger.info("Raw sync '%s' started (%s)", sync_id, sync_type)

        while self.running:
            batch = await self.api.get_markets(
                limit=config.batch_size,
                offset=offset,
                **filters,
            )

            if not batch:
                break

            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y%m%dT%H%M%SZ")
            batch_id = f"{sync_type}-{timestamp}-{offset:08d}"
            key_suffix = f"{sync_type}/{now.strftime('%Y/%m/%d')}/{batch_id}.jsonl"
            s3_key = await self.s3.put_jsonl_batch(
                key_suffix=key_suffix,
                rows=batch,
                metadata={
                    "batch_id": batch_id,
                    "sync_type": sync_type,
                    "offset": str(offset),
                },
            )

            self._record_batch(
                batch_id=batch_id,
                sync_type=sync_type,
                s3_key=s3_key,
                row_count=len(batch),
            )

            total_fetched += len(batch)
            offset += len(batch)
            self._save_sync_state(
                sync_id=sync_id,
                offset=offset,
                total_fetched=total_fetched,
                is_complete=False,
                filters=filters,
            )

            logger.info("Raw batch stored: id=%s rows=%s key=%s", batch_id, len(batch), s3_key)

            if len(batch) < config.batch_size:
                break

            await asyncio.sleep(0.2)

        self._save_sync_state(
            sync_id=sync_id,
            offset=offset,
            total_fetched=total_fetched,
            is_complete=True,
            filters=filters,
        )
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(
            "Raw sync '%s' complete: fetched=%s elapsed=%ss",
            sync_id,
            total_fetched,
            round(elapsed, 2),
        )
        return {
            "sync_id": sync_id,
            "total_fetched": total_fetched,
            "elapsed_seconds": round(elapsed, 2),
            "complete": True,
        }

    async def should_full_sync(self) -> bool:
        last = self._last_full_sync()
        if last is None:
            return True
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return elapsed_hours >= config.full_sync_interval_hours

    async def full_sync(self) -> dict[str, Any]:
        self._clear_state("raw_full_sync")
        return await self._sync(sync_id="raw_full_sync", sync_type="full", filters={})

    async def incremental_sync(self) -> dict[str, Any]:
        self._clear_state("raw_incremental_sync")
        return await self._sync(
            sync_id="raw_incremental_sync",
            sync_type="incremental",
            filters={"closed": "false", "active": "true"},
        )

    async def run(self) -> None:
        self.running = True
        logger.info("Raw ingestion worker loop started")

        while self.running:
            try:
                if await self.should_full_sync():
                    await self.full_sync()
                else:
                    await self.incremental_sync()

                logger.info("Raw worker sleeping %s minutes", config.sync_interval_minutes)
                await asyncio.sleep(config.sync_interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Raw worker loop error: %s", short_error(exc))
                await asyncio.sleep(60)

    def stop(self) -> None:
        self.running = False


async def main() -> None:
    worker = RawIngestionWorker()
    try:
        await worker.connect()
        await worker.run()
    except Exception as exc:
        logger.error("Raw worker failed: %s", short_error(exc))
        raise
    finally:
        await worker.disconnect()
