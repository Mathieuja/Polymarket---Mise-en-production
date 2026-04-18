"""Shared market sync utilities for raw and transform workers."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx
from app_shared.database import Market
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


class GammaAPIClient:
    """Async client for the Polymarket Gamma API."""

    def __init__(self, *, base_url: str, timeout_seconds: float):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_markets(
        self,
        *,
        limit: int,
        offset: int,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        params.update(filters)

        response = await client.get(f"{self.base_url}/markets", params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected markets payload format from Gamma API")
        return payload


def _parse_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _ensure_list(value: Any) -> list[Any]:
    parsed = _parse_json_value(value)
    if isinstance(parsed, list):
        return parsed
    return []


def _ensure_dict(value: Any) -> dict[str, Any]:
    parsed = _parse_json_value(value)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "t"}
    return default


def _json_safe(value: Any) -> Any:
    """Recursively convert Python objects to JSON-serializable values."""

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def _safe_iso_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def transform_market(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform a Gamma API payload into a PostgreSQL row."""

    outcomes = _json_safe(_ensure_list(raw.get("outcomes", [])))
    outcome_prices_raw = _ensure_list(raw.get("outcomePrices", []))
    clob_token_ids = _json_safe(_ensure_list(raw.get("clobTokenIds", [])))
    tags = _json_safe(_ensure_list(raw.get("tags", [])))
    rewards = _json_safe(_ensure_dict(raw.get("rewards", {})))

    outcome_prices = [_safe_float(price) for price in outcome_prices_raw]
    outcome_prices = [price for price in outcome_prices if price is not None]

    external_id = str(
        raw.get("id")
        or raw.get("conditionId")
        or raw.get("slug")
        or raw.get("question")
        or "unknown"
    )
    question = str(raw.get("question") or raw.get("slug") or external_id)
    now = datetime.now(timezone.utc)

    return {
        "external_id": external_id,
        "slug": raw.get("slug"),
        "condition_id": raw.get("conditionId"),
        "question": question,
        "description": raw.get("description"),
        "outcomes": outcomes,
        "outcome_prices": outcome_prices,
        "clob_token_ids": clob_token_ids,
        "tags": tags,
        "rewards": rewards,
        "raw_payload": _json_safe(raw),
        "yes_price": outcome_prices[0] if outcome_prices else _safe_float(raw.get("bestBid")),
        "no_price": outcome_prices[1] if len(outcome_prices) > 1 else None,
        "volume_num": _safe_float(raw.get("volumeNum")),
        "volume_24hr": _safe_float(raw.get("volume24hr")),
        "volume_7d": _safe_float(raw.get("volume7d")),
        "liquidity_num": _safe_float(raw.get("liquidityNum")),
        "best_bid": _safe_float(raw.get("bestBid")),
        "best_ask": _safe_float(raw.get("bestAsk")),
        "spread": _safe_float(raw.get("spread")),
        "closed": _safe_bool(raw.get("closed")),
        "active": _safe_bool(raw.get("active"), default=True),
        "archived": _safe_bool(raw.get("archived")),
        "end_date_iso": _safe_iso_string(raw.get("endDateIso")),
        "start_date_iso": _safe_iso_string(raw.get("startDateIso")),
        "source_created_at": _safe_iso_string(raw.get("createdAt")),
        "image": raw.get("image"),
        "icon": raw.get("icon"),
        "event_slug": raw.get("eventSlug"),
        "group_slug": raw.get("groupSlug"),
        "first_synced_at": now,
        "last_synced_at": now,
        "created_at": now,
        "updated_at": now,
    }


def upsert_markets_batch(session, markets: list[dict[str, Any]]) -> tuple[int, int]:
    """Upsert a batch of markets and return inserted/updated counts."""

    if not markets:
        return 0, 0

    rows = [transform_market(raw_market) for raw_market in markets]
    external_ids = [row["external_id"] for row in rows]
    existing_ids = set(
        session.execute(
            select(Market.external_id).where(Market.external_id.in_(external_ids))
        ).scalars()
    )

    stmt = insert(Market).values(rows)
    update_columns = {
        column.name: getattr(stmt.excluded, column.name)
        for column in Market.__table__.columns
        if column.name not in {"id", "external_id", "created_at", "first_synced_at"}
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=[Market.external_id],
        set_=update_columns,
    )
    session.execute(stmt)

    inserted = sum(1 for external_id in external_ids if external_id not in existing_ids)
    updated = len(rows) - inserted
    return inserted, updated
