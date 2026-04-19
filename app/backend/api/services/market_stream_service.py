"""Redis access helpers for market-stream endpoints."""

from __future__ import annotations

import json
import os
from typing import Any

import redis


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class MarketStreamService:
    """Service that bridges API routes and live_data_worker Redis data."""

    def __init__(self) -> None:
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = _env_int("REDIS_PORT", 6379)
        redis_db = _env_int("REDIS_DB", 0)
        redis_password = os.getenv("REDIS_PASSWORD")

        self.redis_stream_key = os.getenv("REDIS_STREAM_KEY", "polymarket:market_stream")
        self.redis_json_key = os.getenv("REDIS_JSON_KEY", "polymarket:messages_json")
        self.redis_pause_key = os.getenv("REDIS_PAUSE_KEY", "polymarket:worker_paused")
        self.redis_control_channel = os.getenv("REDIS_CONTROL_CHANNEL", "live-data-control")

        self._redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
        )

    def start_stream(self, asset_ids: list[str]) -> None:
        """Clear pause flag and publish start control payload."""

        self._redis.delete(self.redis_pause_key)
        self._redis.publish(
            self.redis_control_channel,
            json.dumps({"asset_ids": asset_ids}),
        )

    def stop_stream(self) -> None:
        """Set pause flag and publish stop control payload."""

        self._redis.set(self.redis_pause_key, "1")
        self._redis.publish(
            self.redis_control_channel,
            json.dumps({"stop": True}),
        )

    def get_orderbook_snapshot(self) -> dict[str, Any]:
        """Return Redis JSON snapshot keyed by token id."""

        payload = self._redis.get(self.redis_json_key)
        if not payload:
            return {}

        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return {}

        if not isinstance(decoded, dict):
            return {}
        return decoded

    def get_latest_message(self) -> dict[str, Any] | None:
        """Return latest message from Redis stream, if available."""

        msgs = self._redis.xrevrange(self.redis_stream_key, count=1)
        if not msgs:
            return None

        _entry_id, fields = msgs[0]
        raw = fields.get("data", "{}")
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if not isinstance(decoded, dict):
            return None
        return decoded
