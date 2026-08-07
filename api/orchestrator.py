"""Bounded cross-market coordination for the API and background scheduler."""

import os

from api.funds import latest_or_refresh as latest_funds_or_refresh
from api.linkage import build_cross_market_overview
from api.llm import LLMConfigurationError, LLMProviderError, analyze_cross_market
from api.market_service import latest_or_refresh
from api.research_evidence import cross_market_bundle
from api.storage import latest_analysis, save_analysis


ANALYSIS_KIND = "cross-market"


def build_context() -> dict:
    market = latest_or_refresh(max_age_seconds=90)
    if market is None:
        raise RuntimeError("stock market snapshot unavailable")
    funds = latest_funds_or_refresh()
    linkage = build_cross_market_overview(market, funds)
    context = {
        "stock_market": {
            key: market.get(key)
            for key in ("as_of", "market_status", "source", "indices", "advancing", "declining", "movers", "sectors")
        },
        "fund_market": {
            "as_of": funds.get("as_of"),
            "source": funds.get("source"),
            "universe_count": funds.get("universe_count"),
            "category_counts": funds.get("category_counts"),
            "funds": funds.get("funds", [])[:60],
        },
        "deterministic_linkage": linkage,
    }
    context["research_evidence"] = cross_market_bundle(market, funds, linkage)
    return context


def run_cross_market_analysis() -> dict:
    result = analyze_cross_market(build_context())
    save_analysis(ANALYSIS_KIND, result)
    return result


def auto_analysis_enabled() -> bool:
    return os.getenv("LLM_AUTO_ANALYSIS", "false").strip().lower() in {"1", "true", "yes", "on"}


def auto_analysis_interval_minutes() -> int:
    try:
        return max(int(os.getenv("LLM_AUTO_ANALYSIS_MINUTES", "3")), 1)
    except ValueError:
        return 3


def latest_cross_market_analysis() -> dict | None:
    return latest_analysis(ANALYSIS_KIND)


__all__ = [
    "LLMConfigurationError",
    "LLMProviderError",
    "auto_analysis_enabled",
    "auto_analysis_interval_minutes",
    "build_context",
    "latest_cross_market_analysis",
    "run_cross_market_analysis",
]
