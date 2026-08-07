"""Small, observable routing state for market-data providers.

The application deliberately keeps a short provider chain.  This module does
not fetch quotes itself; it records each adapter attempt so callers can expose
source freshness and fallback state without coupling the UI to collectors.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from threading import Lock
from typing import TypeVar


T = TypeVar("T")
KNOWN_PROVIDERS = ("akshare", "sina", "eastmoney")
_lock = Lock()
_health: dict[str, dict[str, object]] = {}


def run_provider(name: str, collector: Callable[[], T], *, cooldown_seconds: int) -> T:
    """Run an adapter, applying its cooldown and recording the outcome."""
    now = time.monotonic()
    with _lock:
        record = _health.setdefault(name, {})
        cooldown_until = float(record.get("cooldown_until_monotonic") or 0)
        if cooldown_until > now:
            remaining = max(0, round(cooldown_until - now, 1))
            raise RuntimeError(f"{name} provider is cooling down ({remaining}s remaining)")

    started = time.perf_counter()
    try:
        result = collector()
    except Exception as error:
        _record_failure(name, error, started, cooldown_seconds)
        raise
    _record_success(name, started)
    return result


def _record_success(name: str, started: float) -> None:
    with _lock:
        _health[name] = {
            "status": "ready",
            "last_success_at": datetime.now().astimezone().isoformat(),
            "last_failure_at": _health.get(name, {}).get("last_failure_at"),
            "last_latency_ms": round((time.perf_counter() - started) * 1000),
            "last_error": "",
            "cooldown_until_monotonic": 0.0,
        }


def _record_failure(name: str, error: Exception, started: float, cooldown_seconds: int) -> None:
    with _lock:
        _health[name] = {
            "status": "cooling_down",
            "last_success_at": _health.get(name, {}).get("last_success_at"),
            "last_failure_at": datetime.now().astimezone().isoformat(),
            "last_latency_ms": round((time.perf_counter() - started) * 1000),
            "last_error": str(error)[:180],
            "cooldown_until_monotonic": time.monotonic() + cooldown_seconds,
        }


def provider_statuses() -> list[dict[str, object]]:
    """Return a public, serializable health snapshot for the known chain."""
    now = time.monotonic()
    with _lock:
        result = []
        for name in KNOWN_PROVIDERS:
            record = dict(_health.get(name, {}))
            cooldown_until = float(record.pop("cooldown_until_monotonic", 0) or 0)
            result.append({
                "provider": name,
                "status": record.get("status", "not_checked"),
                "last_success_at": record.get("last_success_at"),
                "last_failure_at": record.get("last_failure_at"),
                "last_latency_ms": record.get("last_latency_ms"),
                "last_error": record.get("last_error", ""),
                "cooldown_remaining_seconds": max(0, round(cooldown_until - now)),
            })
    return result

