"""Typed application settings shared by the local API and collectors."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float(value: str | None, default: float, minimum: float, maximum: float) -> float:
    try:
        return min(max(float(value or default), minimum), maximum)
    except (TypeError, ValueError):
        return default


def _int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        return min(max(int(value or default), minimum), maximum)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    database_path: Path
    api_host: str
    api_port: int
    outbound_proxy: str
    llm_timeout_seconds: float
    llm_auto_analysis: bool
    llm_auto_analysis_minutes: int
    fund_scan_limit: int


def get_settings() -> Settings:
    """Load bounded settings from the configured dotenv file and environment."""
    load_dotenv(os.getenv("MARKET_PULSE_CONFIG_PATH") or None)
    return Settings(
        database_path=Path(os.getenv("MARKET_DB_PATH", "data/market-pulse.sqlite3")).expanduser(),
        api_host=os.getenv("MARKET_PULSE_API_HOST", "127.0.0.1"),
        api_port=_int(os.getenv("MARKET_PULSE_API_PORT"), 8765, 1, 65535),
        outbound_proxy=(os.getenv("OUTBOUND_PROXY") or "").strip(),
        llm_timeout_seconds=_float(os.getenv("LLM_TIMEOUT_SECONDS"), 25, 5, 180),
        llm_auto_analysis=_bool(os.getenv("LLM_AUTO_ANALYSIS")),
        llm_auto_analysis_minutes=_int(os.getenv("LLM_AUTO_ANALYSIS_MINUTES"), 3, 1, 60),
        fund_scan_limit=_int(os.getenv("FUND_SCAN_LIMIT"), 30, 10, 100),
    )
