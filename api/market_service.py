from datetime import datetime

from api.collector import MarketDataError, SHANGHAI, collect_eastmoney_overview
from api.rules import evaluate_rules
from api.storage import daily_histories_for_codes, latest_snapshot, record_rule_events, save_snapshot


def is_trading_session(now: datetime | None = None) -> bool:
    current = (now or datetime.now(SHANGHAI)).astimezone(SHANGHAI)
    if current.weekday() >= 5:
        return False
    minutes = current.hour * 60 + current.minute
    return 570 <= minutes < 690 or 780 <= minutes < 900


def refresh_and_persist() -> dict:
    # AkShare is the preferred full-market source when installed. Its adapter
    # raises MarketDataError on schema/network failure, allowing the stable
    # Eastmoney collector to remain the final fallback.
    try:
        from api.akshare_source import collect_overview as collect_akshare_overview

        snapshot, bars = collect_akshare_overview()
    except (ImportError, MarketDataError):
        snapshot, bars = collect_eastmoney_overview()
    save_snapshot(snapshot, bars)
    signals = evaluate_rules(bars, daily_histories_for_codes([bar["code"] for bar in bars]))
    record_rule_events(signals)
    return snapshot


def latest_or_refresh(max_age_seconds: int = 90) -> dict | None:
    snapshot = latest_snapshot(max_age_seconds=max_age_seconds)
    if snapshot is not None:
        return snapshot
    try:
        return refresh_and_persist()
    except MarketDataError:
        cached = latest_snapshot()
        if cached is not None:
            cached["source"] = "cache"
            cached["is_live"] = False
            return cached
    return None
