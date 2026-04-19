"""
Market service for querying and caching Polymarket data.

Provides:
- Market metadata retrieval with lazy-loading from Gamma API
- Market filtering and pagination
- Price history fetching
- Open interest data
"""
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app_shared.database import Market

from app.backend.api.schemas.market_responses import (
    MarketDetailResponse,
    MarketFilterParams,
    MarketListResponse,
    MarketSummary,
    OpenInterestResponse,
    PriceHistoryResponse,
    SyncStatsResponse,
)
from app.backend.api.services.polymarket_api import get_polymarket_api


class MarketService:
    """Service for market data with PostgreSQL backend."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    # ==================== Market Metadata ====================

    async def get_market_by_slug(
        self,
        slug: str,
        force_refresh: bool = False,
    ) -> Optional[MarketDetailResponse]:
        """
        Get market by slug with lazy-loading.

        Args:
            slug: Market slug identifier
            force_refresh: Force fetch from API even if cached

        Returns:
            MarketDetailResponse or None
        """
        # Check cache first
        market = self.db.query(Market).filter(Market.slug == slug).first()

        if market and not force_refresh:
            return self._market_to_detail_response(market)

        # Fetch from Polymarket API
        api = await get_polymarket_api()
        market_data = await api.get_market_by_slug(slug)

        if not market_data:
            return None

        # Cache and return
        self._cache_market(market_data)
        # Re-fetch from DB to get the cached version
        market = self.db.query(Market).filter(Market.slug == slug).first()
        return self._market_to_detail_response(market) if market else None

    async def get_market_by_condition_id(
        self,
        condition_id: str,
        force_refresh: bool = False,
    ) -> Optional[MarketDetailResponse]:
        """
        Get market by condition ID with lazy-loading.

        Args:
            condition_id: On-chain condition ID
            force_refresh: Force fetch from API even if cached

        Returns:
            MarketDetailResponse or None
        """
        # Check cache first
        market = self.db.query(Market).filter(Market.condition_id == condition_id).first()

        if market and not force_refresh:
            return self._market_to_detail_response(market)

        # Fetch from Polymarket API
        api = await get_polymarket_api()
        market_data = await api.get_market_by_condition_id(condition_id)

        if not market_data:
            return None

        # Cache and return
        self._cache_market(market_data)
        # Re-fetch from DB to get the cached version
        market = self.db.query(Market).filter(Market.condition_id == condition_id).first()
        return self._market_to_detail_response(market) if market else None

    async def list_markets(
        self,
        filters: MarketFilterParams,
    ) -> MarketListResponse:
        """
        List markets with filtering and pagination.
        Queries PostgreSQL database.

        Args:
            filters: Filter and pagination parameters

        Returns:
            MarketListResponse with paginated results
        """
        query = self.db.query(Market)

        # Apply status filters
        if filters.closed is not None:
            query = query.filter(Market.closed == filters.closed)
        if filters.active is not None:
            query = query.filter(Market.active == filters.active)

        # Apply text search (searches both question and description)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Market.question.ilike(search_term),
                    Market.description.ilike(search_term),
                )
            )

        # Apply volume filters
        if filters.volume_min is not None:
            query = query.filter(Market.volume_num >= filters.volume_min)
        if filters.volume_max is not None:
            query = query.filter(Market.volume_num <= filters.volume_max)

        # Apply liquidity filters
        if filters.liquidity_min is not None:
            query = query.filter(Market.liquidity_num >= filters.liquidity_min)
        if filters.liquidity_max is not None:
            query = query.filter(Market.liquidity_num <= filters.liquidity_max)

        # Get total count
        total = query.count()

        # Determine sort field
        sort_field_map = {
            "volume_24h": Market.volume_24hr,
            "volume": Market.volume_num,
            "liquidity": Market.liquidity_num,
            "end_date": Market.end_date_iso,
        }
        sort_field = sort_field_map.get(filters.sort_by or "volume", Market.volume_num)
        sort_dir = sort_field.desc() if filters.sort_desc else sort_field.asc()

        # Apply pagination and sorting
        skip = (filters.page - 1) * filters.page_size
        total_pages = (total + filters.page_size - 1) // filters.page_size

        markets = (
            query.order_by(sort_dir)
            .offset(skip)
            .limit(filters.page_size)
            .all()
        )

        market_summaries = [self._market_to_summary(m) for m in markets]

        return MarketListResponse(
            markets=market_summaries,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_prev=filters.page > 1,
        )

    async def get_top_markets(
        self,
        limit: int = 20,
        sort_by: str = "volume_24h",
        active_only: bool = True,
    ) -> list[MarketSummary]:
        """
        Get top markets by volume or liquidity.

        Args:
            limit: Number of markets to return
            sort_by: Field to sort by (volume_24h, liquidity, etc.)
            active_only: Only return active markets

        Returns:
            List of MarketSummary
        """
        query = self.db.query(Market)

        if active_only:
            query = query.filter(and_(Market.closed == False, Market.active == True))

        # Map friendly names to DB fields
        sort_field_map = {
            "volume_24h": Market.volume_24hr,
            "volume": Market.volume_num,
            "liquidity": Market.liquidity_num,
            "end_date": Market.end_date_iso,
        }
        sort_field = sort_field_map.get(sort_by, Market.volume_num)

        markets = (
            query.order_by(sort_field.desc())
            .limit(limit)
            .all()
        )

        return [self._market_to_summary(m) for m in markets]

    # ==================== Price History ====================

    async def get_price_history(
        self,
        slug: str,
        outcome_index: int = 0,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        force_refresh: bool = False,
    ) -> Optional[PriceHistoryResponse]:
        """
        Get price history for a market outcome.

        Note: Price history is not persisted in this version.
        Each call fetches from the API on demand.

        Args:
            slug: Market slug
            outcome_index: Outcome index (0 or 1 for binary markets)
            start_ts: Start Unix timestamp filter
            end_ts: End Unix timestamp filter
            force_refresh: Ignored (always fetches from API)

        Returns:
            PriceHistoryResponse or None
        """
        # Get market to find token ID
        market = self.db.query(Market).filter(Market.slug == slug).first()

        if not market:
            # Try fetching from API
            api = await get_polymarket_api()
            market_data = await api.get_market_by_slug(slug)
            if not market_data:
                return None
            await self._cache_market(market_data)
            market = self.db.query(Market).filter(Market.slug == slug).first()
            if not market:
                return None

        clob_token_ids = market.clob_token_ids or []
        outcomes = market.outcomes or []

        # If no token IDs available, return empty history
        if not clob_token_ids or outcome_index >= len(clob_token_ids):
            outcome_name = outcomes[outcome_index] if outcome_index < len(outcomes) else f"Outcome {outcome_index}"
            return PriceHistoryResponse(
                slug=slug,
                outcome=outcome_name,
                outcome_index=outcome_index,
                token_id="",
                history=[],
                total_points=0,
                cached_at=None,
            )

        token_id = clob_token_ids[outcome_index]
        outcome_name = outcomes[outcome_index] if outcome_index < len(outcomes) else f"Outcome {outcome_index}"

        # Fetch from CLOB API
        api = await get_polymarket_api()
        try:
            history = await api.get_price_history(
                token_id,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        except Exception:
            # Return empty history on error
            return PriceHistoryResponse(
                slug=slug,
                outcome=outcome_name,
                outcome_index=outcome_index,
                token_id=token_id,
                history=[],
                total_points=0,
                cached_at=None,
            )

        # Filter history by timestamp range
        filtered_history = self._filter_history(history, start_ts, end_ts)

        return PriceHistoryResponse(
            slug=slug,
            outcome=outcome_name,
            outcome_index=outcome_index,
            token_id=token_id,
            history=filtered_history,
            total_points=len(filtered_history),
            cached_at=datetime.now(timezone.utc),
        )

    def _filter_history(
        self,
        history: list[dict],
        start_ts: Optional[int],
        end_ts: Optional[int],
    ) -> list[dict]:
        """Filter price history by timestamp range."""
        if not start_ts and not end_ts:
            return history

        filtered = []
        for point in history:
            ts = point.get("t", 0)
            if start_ts and ts < start_ts:
                continue
            if end_ts and ts > end_ts:
                continue
            filtered.append(point)

        return filtered

    # ==================== Open Interest ====================

    async def get_open_interest(
        self,
        slugs: list[str],
        force_refresh: bool = False,
    ) -> list[OpenInterestResponse]:
        """
        Get open interest for multiple markets.

        Args:
            slugs: List of market slugs
            force_refresh: Force fetch from API

        Returns:
            List of OpenInterestResponse
        """
        # Get condition IDs for the slugs
        markets = self.db.query(Market).filter(Market.slug.in_(slugs)).all()
        slug_to_cond = {m.slug: m.condition_id for m in markets if m.condition_id}

        if not slug_to_cond:
            return []

        condition_ids = list(slug_to_cond.values())

        # Fetch from Data API
        api = await get_polymarket_api()
        try:
            oi_data = await api.get_open_interest(condition_ids)
        except Exception:
            # Return empty list on error
            return []

        results: list[OpenInterestResponse] = []
        now = datetime.now(timezone.utc)

        for item in oi_data:
            cond_id = item.get("market")
            value = item.get("value")
            slug = next((s for s, c in slug_to_cond.items() if c == cond_id), None)

            if slug and value is not None:
                results.append(OpenInterestResponse(
                    slug=slug,
                    condition_id=cond_id,
                    value=value,
                    fetched_at=now,
                ))

        return results

    # ==================== Statistics ====================

    async def get_sync_stats(self) -> SyncStatsResponse:
        """Get market database sync statistics."""
        total = self.db.query(func.count(Market.id)).scalar() or 0
        active = self.db.query(func.count(Market.id)).filter(
            and_(Market.closed == False, Market.active == True)
        ).scalar() or 0
        closed = self.db.query(func.count(Market.id)).filter(
            Market.closed == True
        ).scalar() or 0

        # Get oldest and newest sync times
        oldest_sync = self.db.query(func.min(Market.last_synced_at)).scalar()
        newest_sync = self.db.query(func.max(Market.last_synced_at)).scalar()

        return SyncStatsResponse(
            total_markets=total,
            active_markets=active,
            closed_markets=closed,
            oldest_sync=oldest_sync,
            newest_sync=newest_sync,
        )

    # ==================== Private Helpers ====================

    def _cache_market(self, market_data: dict[str, Any]) -> None:
        """
        Cache a single market to PostgreSQL.

        Creates or updates a market record.
        """
        # Extract key fields from Gamma API response
        slug = market_data.get("slug", "")
        if not slug:
            return

        external_id = market_data.get("id", "") or slug

        # Parse outcomes and prices
        outcomes = market_data.get("outcomes", [])
        if isinstance(outcomes, str):
            try:
                import json
                outcomes = json.loads(outcomes) if outcomes else []
            except Exception:
                outcomes = []

        outcome_prices = market_data.get("outcomePrices", [])
        if isinstance(outcome_prices, str):
            try:
                import json
                outcome_prices = json.loads(outcome_prices) if outcome_prices else []
            except Exception:
                outcome_prices = []

        clob_token_ids = market_data.get("clobTokenIds", [])
        if isinstance(clob_token_ids, str):
            try:
                import json
                clob_token_ids = json.loads(clob_token_ids) if clob_token_ids else []
            except Exception:
                clob_token_ids = []

        # Check if market exists
        market = self.db.query(Market).filter(Market.slug == slug).first()

        if market:
            # Update existing
            market.external_id = external_id
            market.condition_id = market_data.get("conditionId")
            market.question = market_data.get("question", market.question)
            market.description = market_data.get("description")
            market.outcomes = outcomes
            market.outcome_prices = outcome_prices
            market.clob_token_ids = clob_token_ids
            market.volume_num = float(market_data.get("volumeNum", 0) or 0)
            market.volume_24hr = float(market_data.get("volume24hr", 0) or 0)
            market.volume_7d = float(market_data.get("volume7d", 0) or 0)
            market.liquidity_num = float(market_data.get("liquidityNum", 0) or 0)
            market.best_bid = float(market_data["bestBid"]) if market_data.get("bestBid") is not None else None
            market.best_ask = float(market_data["bestAsk"]) if market_data.get("bestAsk") is not None else None
            market.spread = float(market_data["spread"]) if market_data.get("spread") is not None else None
            market.active = market_data.get("active", True)
            market.closed = market_data.get("closed", False)
            market.image = market_data.get("image")
            market.icon = market_data.get("icon")
            market.end_date_iso = market_data.get("endDate")
            market.start_date_iso = market_data.get("startDate")
            market.source_created_at = market_data.get("createdAt")
            market.last_synced_at = datetime.utcnow()
        else:
            # Create new
            market = Market(
                external_id=external_id,
                slug=slug,
                condition_id=market_data.get("conditionId"),
                question=market_data.get("question", ""),
                description=market_data.get("description"),
                outcomes=outcomes,
                outcome_prices=outcome_prices,
                clob_token_ids=clob_token_ids,
                volume_num=float(market_data.get("volumeNum", 0) or 0),
                volume_24hr=float(market_data.get("volume24hr", 0) or 0),
                volume_7d=float(market_data.get("volume7d", 0) or 0),
                liquidity_num=float(market_data.get("liquidityNum", 0) or 0),
                best_bid=float(market_data["bestBid"]) if market_data.get("bestBid") is not None else None,
                best_ask=float(market_data["bestAsk"]) if market_data.get("bestAsk") is not None else None,
                spread=float(market_data["spread"]) if market_data.get("spread") is not None else None,
                active=market_data.get("active", True),
                closed=market_data.get("closed", False),
                image=market_data.get("image"),
                icon=market_data.get("icon"),
                end_date_iso=market_data.get("endDate"),
                start_date_iso=market_data.get("startDate"),
                source_created_at=market_data.get("createdAt"),
                last_synced_at=datetime.utcnow(),
            )
            self.db.add(market)

        self.db.commit()

    def _market_to_summary(self, market: Market) -> MarketSummary:
        """Convert Market ORM model to MarketSummary schema."""
        return MarketSummary(
            slug=market.slug or "",
            question=market.question or "",
            outcomes=market.outcomes or [],
            outcome_prices=[str(p) for p in (market.outcome_prices or [])],
            volume_24h=market.volume_24hr,
            volume_total=market.volume_num,
            liquidity=market.liquidity_num,
            best_bid=market.best_bid,
            best_ask=market.best_ask,
            spread=market.spread,
            closed=market.closed or False,
            active=market.active or True,
            end_date=self._parse_iso_date(market.end_date_iso),
        )

    def _market_to_detail_response(self, market: Market) -> MarketDetailResponse:
        """Convert Market ORM model to MarketDetailResponse schema."""
        return MarketDetailResponse(
            slug=market.slug or "",
            condition_id=market.condition_id,
            question=market.question or "",
            description=market.description,
            outcomes=market.outcomes or [],
            outcome_prices=[str(p) for p in (market.outcome_prices or [])],
            clob_token_ids=market.clob_token_ids or [],
            volume_24h=market.volume_24hr,
            volume_7d=market.volume_7d,
            volume_total=market.volume_num,
            liquidity=market.liquidity_num,
            best_bid=market.best_bid,
            best_ask=market.best_ask,
            spread=market.spread,
            closed=market.closed or False,
            active=market.active or True,
            end_date=self._parse_iso_date(market.end_date_iso),
            image=market.image,
            icon=market.icon,
            tags=market.tags or [],
            rewards=market.rewards or {},
            last_synced_at=market.last_synced_at,
        )

    @staticmethod
    def _parse_iso_date(value: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string to datetime."""
        if not value:
            return None
        try:
            if isinstance(value, str):
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
        return None
