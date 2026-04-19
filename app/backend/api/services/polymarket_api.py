"""
Polymarket API client for fetching market data.

This client wraps the Polymarket REST APIs:
- Gamma API: Market metadata (https://gamma-api.polymarket.com)
- CLOB API: Price history (https://clob.polymarket.com)
- Data API: Open interest (https://data-api.polymarket.com)

All endpoints use public REST access (no authentication required).
"""
from typing import Any, Optional

import httpx

# API Base URLs
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
DATA_BASE = "https://data-api.polymarket.com"


class PolymarketAPI:
    """Async client for Polymarket REST APIs."""

    def __init__(self):
        """Initialize Polymarket API client."""
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ==================== Gamma API: Market Metadata ====================

    async def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        closed: Optional[bool] = None,
        active: Optional[bool] = None,
        slug: Optional[str] = None,
        condition_id: Optional[str] = None,
        volume_num_min: Optional[float] = None,
        volume_num_max: Optional[float] = None,
        liquidity_num_min: Optional[float] = None,
        liquidity_num_max: Optional[float] = None,
        **extra_filters,
    ) -> list[dict[str, Any]]:
        """
        Fetch list of markets from Gamma API.

        Args:
            limit: Max results per page (default 100)
            offset: Pagination offset
            closed: Filter by closed status
            active: Filter by active status
            slug: Filter by exact slug
            condition_id: Filter by condition ID
            volume_num_min/max: Volume filters
            liquidity_num_min/max: Liquidity filters
            **extra_filters: Additional Gamma API filters

        Returns:
            List of market metadata dicts
        """
        client = await self._get_client()

        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if closed is not None:
            params["closed"] = str(closed).lower()
        if active is not None:
            params["active"] = str(active).lower()
        if slug:
            params["slug"] = slug
        if condition_id:
            params["condition_ids"] = condition_id
        if volume_num_min is not None:
            params["volume_num_min"] = volume_num_min
        if volume_num_max is not None:
            params["volume_num_max"] = volume_num_max
        if liquidity_num_min is not None:
            params["liquidity_num_min"] = liquidity_num_min
        if liquidity_num_max is not None:
            params["liquidity_num_max"] = liquidity_num_max

        params.update(extra_filters)

        response = await client.get(f"{GAMMA_BASE}/markets", params=params)
        response.raise_for_status()
        return response.json()

    async def get_market_by_slug(self, slug: str) -> Optional[dict[str, Any]]:
        """
        Get a single market by slug.

        Args:
            slug: Market slug identifier

        Returns:
            Market metadata dict or None if not found
        """
        markets = await self.get_markets(limit=1, slug=slug)
        return markets[0] if markets else None

    async def get_market_by_condition_id(self, condition_id: str) -> Optional[dict[str, Any]]:
        """
        Get a single market by condition ID.

        Args:
            condition_id: On-chain condition ID

        Returns:
            Market metadata dict or None if not found
        """
        markets = await self.get_markets(limit=1, condition_id=condition_id)
        return markets[0] if markets else None

    async def get_all_markets_paginated(
        self,
        batch_size: int = 100,
        max_markets: Optional[int] = None,
        **filters,
    ) -> list[dict[str, Any]]:
        """
        Fetch all markets with automatic pagination.

        Args:
            batch_size: Markets per request
            max_markets: Maximum total markets to fetch (None = all)
            **filters: Filters to apply

        Returns:
            List of market dicts
        """
        all_markets = []
        offset = 0

        while True:
            batch = await self.get_markets(
                limit=batch_size,
                offset=offset,
                **filters,
            )

            if not batch:
                break

            all_markets.extend(batch)
            offset += len(batch)

            if max_markets and len(all_markets) >= max_markets:
                all_markets = all_markets[:max_markets]
                break

            if len(batch) < batch_size:
                break

        return all_markets

    # ==================== CLOB API: Price History ====================

    async def get_price_history(
        self,
        token_id: str,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        interval: Optional[str] = None,
        fidelity: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Get price history for a CLOB token.

        Args:
            token_id: CLOB token ID (from clobTokenIds)
            start_ts: Start Unix timestamp
            end_ts: End Unix timestamp
            interval: Time interval ('1h', '6h', '1d', 'max')
            fidelity: Minute resolution

        Returns:
            List of price points: [{'t': timestamp, 'p': price}, ...]
        """
        client = await self._get_client()

        params: dict[str, Any] = {
            "id": token_id,
        }

        if start_ts is not None:
            params["startTs"] = start_ts
        if end_ts is not None:
            params["endTs"] = end_ts
        if interval:
            params["interval"] = interval
        if fidelity is not None:
            params["fidelity"] = fidelity

        response = await client.get(f"{CLOB_BASE}/prices", params=params)
        response.raise_for_status()

        data = response.json()
        # Normalize response format
        if isinstance(data, dict):
            return data.get("prices", [])
        return data

    # ==================== Data API: Open Interest ====================

    async def get_open_interest(
        self,
        condition_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        Get open interest for markets.

        Args:
            condition_ids: List of market condition IDs

        Returns:
            List of dicts: [{'market': condition_id, 'value': float}, ...]
        """
        client = await self._get_client()

        params = {"market": ",".join(condition_ids)}
        response = await client.get(f"{DATA_BASE}/oi", params=params)
        response.raise_for_status()

        return response.json()

    async def get_open_interest_single(
        self,
        condition_id: str,
    ) -> Optional[float]:
        """
        Get open interest for a single market.

        Args:
            condition_id: Market condition ID

        Returns:
            Open interest value or None
        """
        results = await self.get_open_interest([condition_id])
        for item in results:
            if item.get("market") == condition_id:
                return item.get("value")
        return None


# Singleton instance for shared use
_polymarket_api: Optional[PolymarketAPI] = None


async def get_polymarket_api() -> PolymarketAPI:
    """Get shared PolymarketAPI instance."""
    global _polymarket_api
    if _polymarket_api is None:
        _polymarket_api = PolymarketAPI()
    return _polymarket_api
