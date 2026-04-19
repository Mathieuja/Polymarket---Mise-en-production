"""Live data worker: CLOB websocket -> Redis stream + Redis JSON snapshot."""

from __future__ import annotations

import asyncio
import json
import ssl
import threading
from datetime import datetime, timezone
from typing import Any

import redis
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from websocket import WebSocketApp

from .logging_utils import configure_worker_logging, short_error


class LiveDataWorkerConfig(BaseSettings):
    """Configuration for CLOB live-data ingestion to Redis."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: str | None = Field(default=None)

    redis_stream_key: str = Field(default="polymarket:market_stream")
    redis_json_key: str = Field(default="polymarket:messages_json")
    redis_control_channel: str = Field(default="live-data-control")
    stream_max_len: int = Field(default=10000)

    clob_ws_url: str = Field(default="wss://ws-subscriptions-clob.polymarket.com/ws/market")
    clob_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("API_KEY", "POLYMARKET_API_KEY"),
    )
    clob_subscription_type: str = Field(default="market")

    reconnect_base_delay_seconds: float = Field(default=1.0)
    reconnect_max_delay_seconds: float = Field(default=60.0)
    paused_poll_seconds: float = Field(default=2.0)

    log_level: str = Field(default="INFO")
    console_log_level: str = Field(default="INFO")
    log_file: str = Field(default="/tmp/polymarket-live-data-worker.log")


config = LiveDataWorkerConfig()


logger = configure_worker_logging(
    logger_name="polymarket_live_data_worker",
    log_level=config.log_level,
    console_log_level=config.console_log_level,
    log_file=config.log_file,
)


class JSONStorageManager:
    """Manages a Redis JSON snapshot of orderbooks by asset id."""

    def __init__(self, redis_client: redis.Redis, redis_key: str) -> None:
        self.redis_client = redis_client
        self.redis_key = redis_key
        self._lock = threading.Lock()

        if not self.redis_client.exists(redis_key):
            self.redis_client.set(redis_key, json.dumps({}))

    def update_orderbook(
        self,
        message: dict[str, Any],
        preferred_order: list[str] | None = None,
    ) -> None:
        """Apply snapshot or incremental CLOB orderbook updates into Redis JSON."""

        with self._lock:
            payload = self.redis_client.get(self.redis_key)
            data = json.loads(payload or "{}")

            if "bids" in message or "asks" in message:
                asset_id = message.get("asset_id")
                if asset_id:
                    data[asset_id] = {
                        "bids": {
                            str(bid["price"]): str(bid["size"])
                            for bid in message.get("bids", [])
                            if "price" in bid and "size" in bid
                        },
                        "asks": {
                            str(ask["price"]): str(ask["size"])
                            for ask in message.get("asks", [])
                            if "price" in ask and "size" in ask
                        },
                    }

            elif "price_changes" in message:
                for change in message["price_changes"]:
                    asset_id = change.get("asset_id")
                    if not asset_id:
                        continue

                    if asset_id not in data:
                        data[asset_id] = {"bids": {}, "asks": {}}

                    side = str(change.get("side", "")).upper()
                    price = str(change.get("price"))
                    size = str(change.get("size"))

                    if side == "BUY":
                        data[asset_id]["bids"][price] = size
                    elif side == "SELL":
                        data[asset_id]["asks"][price] = size

            if preferred_order:
                ordered_data: dict[str, Any] = {}
                for asset_id in preferred_order:
                    if asset_id in data and asset_id not in ordered_data:
                        ordered_data[asset_id] = data[asset_id]
                for key in data:
                    if key not in ordered_data:
                        ordered_data[key] = data[key]
                data = ordered_data

            self.redis_client.set(self.redis_key, json.dumps(data))

    def clear(self) -> None:
        """Clear the orderbook snapshot."""

        with self._lock:
            self.redis_client.set(self.redis_key, json.dumps({}))


class PolymarketWebSocketManager:
    """Handles websocket consumption and Redis persistence."""

    def __init__(self, redis_client: redis.Redis, json_manager: JSONStorageManager) -> None:
        self.redis_client = redis_client
        self.json_manager = json_manager
        self.ws: WebSocketApp | None = None
        self.asset_ids: list[str] = []
        self.paused = True
        self._control_thread: threading.Thread | None = None

    def _auth_headers(self) -> list[str] | None:
        if not config.clob_api_key:
            return None
        return [f"Authorization: Bearer {config.clob_api_key}"]

    def _on_message(self, _ws: WebSocketApp, message: str) -> None:
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return

        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"ping", "pong"}:
                continue

            try:
                self.redis_client.xadd(
                    config.redis_stream_key,
                    {
                        "data": json.dumps(item, ensure_ascii=False, default=str),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    maxlen=config.stream_max_len,
                    approximate=True,
                )

                preferred = self.asset_ids if self.asset_ids else None
                self.json_manager.update_orderbook(item, preferred_order=preferred)
            except Exception as exc:
                logger.error("Failed to persist websocket message: %s", short_error(exc))

    def _on_open(self, ws: WebSocketApp) -> None:
        if self.asset_ids:
            ws.send(
                json.dumps(
                    {
                        "assets_ids": self.asset_ids,
                        "type": config.clob_subscription_type,
                    }
                )
            )
            logger.info("Subscribed to %s assets", len(self.asset_ids))

    def _connect_blocking(self) -> None:
        self.ws = WebSocketApp(
            config.clob_ws_url,
            header=self._auth_headers(),
            on_message=self._on_message,
            on_error=lambda _ws, err: logger.error("WS error: %s", err),
            on_close=lambda _ws, code, msg: logger.warning("WS closed %s %s", code, msg),
            on_open=self._on_open,
        )
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_REQUIRED})

    async def connect(self) -> bool:
        try:
            await asyncio.to_thread(self._connect_blocking)
            return True
        except Exception as exc:
            logger.error("Failed websocket connection: %s", short_error(exc))
            return False

    def disconnect(self) -> None:
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

    def start_control_listener(self) -> None:
        """Listens to control channel to start/stop or update subscribed assets."""

        if self._control_thread and self._control_thread.is_alive():
            return

        def _listen() -> None:
            pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(config.redis_control_channel)
            logger.info("Subscribed to control channel '%s'", config.redis_control_channel)

            for message in pubsub.listen():
                if not message or "data" not in message:
                    continue

                data = message["data"]
                if not data:
                    continue

                try:
                    raw = data.decode() if isinstance(data, bytes) else data
                    payload = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

                if not isinstance(payload, dict):
                    continue

                if payload.get("stop"):
                    logger.info("Stop requested from control channel, clearing Redis live keys")
                    self.paused = True
                    try:
                        self.redis_client.delete(config.redis_stream_key)
                    except Exception:
                        pass
                    try:
                        self.json_manager.clear()
                    except Exception:
                        pass
                    if self.ws:
                        try:
                            self.ws.close()
                        except Exception:
                            pass
                    continue

                new_asset_ids = payload.get("asset_ids") or payload.get("assets_ids")
                if new_asset_ids:
                    self.asset_ids = [
                        str(asset_id).strip()
                        for asset_id in new_asset_ids
                        if asset_id
                    ]
                    self.paused = False

                    if self.ws:
                        try:
                            self.ws.send(
                                json.dumps(
                                    {
                                        "assets_ids": self.asset_ids,
                                        "type": config.clob_subscription_type,
                                    }
                                )
                            )
                        except Exception:
                            pass

        self._control_thread = threading.Thread(target=_listen, daemon=True)
        self._control_thread.start()


class LiveDataWorker:
    """Long-running worker that feeds Redis with live CLOB market updates."""

    def __init__(self) -> None:
        self.running = False
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True,
        )
        self.json_manager = JSONStorageManager(self.redis_client, config.redis_json_key)
        self.ws_manager = PolymarketWebSocketManager(self.redis_client, self.json_manager)
        self._paused_logged = False

    async def connect(self) -> None:
        await asyncio.to_thread(self.redis_client.ping)
        self.ws_manager.start_control_listener()
        logger.info(
            "Live data worker connected to Redis at %s:%s",
            config.redis_host,
            config.redis_port,
        )

    async def disconnect(self) -> None:
        self.ws_manager.disconnect()
        await asyncio.to_thread(self.redis_client.close)
        logger.info("Live data worker disconnected")

    async def run(self) -> None:
        self.running = True
        reconnect_delay = config.reconnect_base_delay_seconds
        logger.info("Live data worker loop started")

        while self.running:
            if self.ws_manager.paused:
                if not self._paused_logged:
                    logger.info("Live data worker paused; waiting for asset_ids on control channel")
                    self._paused_logged = True
                await asyncio.sleep(config.paused_poll_seconds)
                continue

            if self._paused_logged:
                logger.info("Live data worker resumed")
                self._paused_logged = False

            ok = await self.ws_manager.connect()
            if ok:
                reconnect_delay = config.reconnect_base_delay_seconds
            else:
                logger.warning("Retry websocket connection in %ss", reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    config.reconnect_max_delay_seconds,
                )

    def stop(self) -> None:
        self.running = False
        self.ws_manager.disconnect()


async def main() -> None:
    worker = LiveDataWorker()
    try:
        await worker.connect()
        await worker.run()
    except Exception as exc:
        logger.error("Live data worker failed: %s", short_error(exc))
        raise
    finally:
        await worker.disconnect()
