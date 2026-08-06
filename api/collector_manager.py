"""Tiered collector facade with provider fallback and memory TTLs."""

from enum import Enum
from typing import Any

from api.collector import MarketDataError, _collect_indices
from api.collector_cache import MemoryCache
from api.akshare_source import fetch_indices as fetch_akshare_indices
from api.sina_source import fetch_indices


class Tier(str, Enum):
    WATCHLIST = "watchlist"
    INDICES = "indices"
    MARKET_BREADTH = "breadth"
    FULL_SCAN = "full_scan"
    FUNDS = "funds"
    EOD = "eod"


TIER_TTLS = {
    Tier.WATCHLIST: 10,
    Tier.INDICES: 10,
    Tier.MARKET_BREADTH: 60,
    Tier.FULL_SCAN: 300,
    Tier.FUNDS: 300,
    Tier.EOD: 86_400,
}


class CollectorManager:
    def __init__(self) -> None:
        self.cache = MemoryCache()

    def gather(self, tier: Tier) -> Any:
        cached = self.cache.get(tier.value)
        if cached is not None:
            return cached
        if tier is Tier.INDICES:
            result = self._try_index_sources()
            self.cache.set(tier.value, result, TIER_TTLS[tier])
            return result
        raise MarketDataError(f"Tier {tier.value} has no provider adapter yet")

    def _try_index_sources(self) -> list[dict]:
        errors: list[str] = []
        for provider in (fetch_akshare_indices, fetch_indices, _collect_indices):
            try:
                result = provider()
                if result:
                    return result
            except MarketDataError as error:
                errors.append(str(error))
        fallback = self.cache.get_fallback(Tier.INDICES.value)
        if fallback is not None:
            return fallback
        raise MarketDataError("All index providers failed: " + "; ".join(errors))


_manager = CollectorManager()


def get_collector_manager() -> CollectorManager:
    return _manager
