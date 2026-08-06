"""Sina quote fallback for the major A-share indices."""

import re
from urllib.request import Request

from api.collector import MarketDataError, _format_change, _format_price, _number
from api.network import open_url


SINA_INDEX_CODES = {
    "s_sh000001": "上证指数",
    "s_sz399001": "深证成指",
    "s_sz399006": "创业板指",
    "s_sh000688": "科创50",
}
SINA_URL = "https://hq.sinajs.cn/list="


def parse_index_payload(text: str) -> list[dict]:
    """Parse Sina's GBK/latin-compatible hq text into normalized indices."""
    result = []
    for symbol, name in SINA_INDEX_CODES.items():
        match = re.search(rf'var\s+hq_str_{re.escape(symbol)}="([^"]*)";', text)
        if match is None:
            continue
        fields = match.group(1).split(",")
        if len(fields) < 4:
            continue
        current = _number(fields[3])
        previous = _number(fields[2])
        change = ((current / previous) - 1) * 100 if previous else 0
        result.append({
            "name": name,
            "value": _format_price(current),
            "change": _format_change(change),
            "direction": "up" if change >= 0 else "down",
        })
    if not result:
        raise MarketDataError("Sina index response was empty")
    return result


def fetch_indices() -> list[dict]:
    symbols = ",".join(SINA_INDEX_CODES)
    request = Request(
        f"{SINA_URL}{symbols}",
        headers={"User-Agent": "MarketPulse/0.2", "Referer": "https://finance.sina.com.cn/"},
    )
    try:
        with open_url(request, timeout=8) as response:
            raw = response.read()
            return parse_index_payload(raw.decode("gbk", errors="replace"))
    except Exception as error:
        raise MarketDataError("Sina index data is temporarily unavailable") from error
