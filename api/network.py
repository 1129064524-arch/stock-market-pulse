"""Shared outbound HTTP configuration.

All provider requests go through :func:`open_url` so a single proxy setting
controls the whole backend.  ``NO_PROXY`` keeps the standard bypass behavior.
"""

from __future__ import annotations

import os
from urllib.request import OpenerDirector, ProxyHandler, Request, build_opener

from dotenv import load_dotenv


load_dotenv()


def proxy_url() -> str:
    """Return the configured outbound proxy, if one is available.

    ``OUTBOUND_PROXY`` is the application setting.  The aliases make the
    service work with common shell and container conventions as well.
    """

    for name in ("OUTBOUND_PROXY", "PROXY_URL", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _build_opener() -> OpenerDirector:
    configured_proxy = proxy_url()
    if not configured_proxy:
        # An empty ProxyHandler delegates to urllib's normal environment-aware
        # behavior while still giving us one shared request entry point.
        return build_opener(ProxyHandler())
    return build_opener(ProxyHandler({"http": configured_proxy, "https": configured_proxy}))


def open_url(request: Request, *, timeout: float) -> object:
    """Open an outbound request, falling back to direct access if a proxy is down."""

    configured_proxy = proxy_url()
    try:
        return _build_opener().open(request, timeout=timeout)
    except Exception:
        if not configured_proxy:
            raise
        # A stale desktop proxy should not turn every public provider into
        # demo mode. Empty ProxyHandler disables environment proxy variables.
        return build_opener(ProxyHandler({})).open(request, timeout=timeout)
