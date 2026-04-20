from __future__ import annotations

import asyncio
from typing import Optional

from app_shared.database import SessionLocal, User
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.backend.api.core.security import decode_access_token
from app.backend.api.services.market_stream_service import MarketStreamService

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, user_key: str) -> None:
        await websocket.accept()
        self.active_connections[user_key] = websocket
        self.subscriptions[user_key] = set()

    def disconnect(self, user_key: str) -> None:
        self.active_connections.pop(user_key, None)
        self.subscriptions.pop(user_key, None)


manager = ConnectionManager()


def _resolve_user_from_token(token: str) -> Optional[User]:
    try:
        payload = decode_access_token(token)
    except ValueError:
        return None

    email = str(payload.get("sub") or "").strip().lower()
    if not email:
        return None

    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()


@router.websocket("/ws/live")
async def websocket_live_data(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    user = _resolve_user_from_token(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_key = str(user.id)
    await manager.connect(websocket, user_key)

    await websocket.send_json(
        {
            "type": "connected",
            "user_id": user_key,
            "message": "Connected to live data stream",
        }
    )

    stream_service = MarketStreamService()

    async def _push_loop() -> None:
        try:
            while True:
                await asyncio.sleep(2)
                latest = stream_service.get_latest_message()
                if latest is None:
                    continue
                await websocket.send_json({"type": "latest", "data": latest})
        except asyncio.CancelledError:
            return
        except Exception:
            return

    push_task = asyncio.create_task(_push_loop())

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "subscribe":
                market_ids = [str(item) for item in data.get("market_ids", [])]
                manager.subscriptions[user_key].update(market_ids)
                await websocket.send_json({"type": "subscribed", "market_ids": market_ids})
            elif action == "unsubscribe":
                market_ids = [str(item) for item in data.get("market_ids", [])]
                manager.subscriptions[user_key].difference_update(market_ids)
                await websocket.send_json({"type": "unsubscribed", "market_ids": market_ids})
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({"type": "error", "message": "Unknown action"})
    except WebSocketDisconnect:
        pass
    finally:
        push_task.cancel()
        manager.disconnect(user_key)
