"""Sina quote fallback for major indices and the full A-share market."""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request
from zoneinfo import ZoneInfo

from api.collector import MarketDataError, _format_change, _format_price, _number
from api.network import open_url


SINA_INDEX_CODES = {
    "s_sh000001": "上证指数",
    "s_sz399001": "深证成指",
    "s_sz399006": "创业板指",
    "s_sh000688": "科创50",
}
SINA_URL = "https://hq.sinajs.cn/list="
SINA_MARKET_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
SHANGHAI = ZoneInfo("Asia/Shanghai")


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
        # The compact ``s_`` feed is: name, current, change points,
        # change percent, volume, amount.
        current = _number(fields[1])
        change = _number(fields[3])
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


def _fetch_stock_page(page: int, page_size: int = 100) -> list[dict]:
    query = urlencode({"page": page, "num": page_size, "sort": "changepercent", "asc": "0", "node": "hs_a", "symbol": ""})
    request = Request(
        f"{SINA_MARKET_URL}?{query}",
        headers={"User-Agent": "Mozilla/5.0 MarketPulse/0.2", "Referer": "https://finance.sina.com.cn/"},
    )
    with open_url(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def fetch_all_stocks(max_pages: int = 60) -> list[dict]:
    records = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(_fetch_stock_page, page) for page in range(1, max_pages + 1)]
        for future in as_completed(futures):
            try:
                records.extend(future.result())
            except Exception:
                continue
    normalized = []
    seen = set()
    for row in records:
        code = str(row.get("code") or "").zfill(6)
        price = _number(row.get("trade"))
        if len(code) != 6 or code in seen or price <= 0:
            continue
        seen.add(code)
        normalized.append({
            "code": code, "name": str(row.get("name") or code), "price": price,
            "change_pct": _number(row.get("changepercent")), "amount": _number(row.get("amount")),
            "turnover": _number(row.get("turnoverratio")), "industry": "全市场", "source": "sina",
        })
    if len(normalized) < 1000:
        raise MarketDataError(f"Sina full-market response was incomplete ({len(normalized)})")
    return normalized


def collect_overview() -> tuple[dict, list[dict]]:
    from api.collector import _format_amount, _market_status, _score, _signal

    records = fetch_all_stocks()
    now = datetime.now(SHANGHAI)
    movers = []
    for item in sorted(records, key=lambda row: abs(row["change_pct"]), reverse=True)[:12]:
        signal, note, risk = _signal(item["change_pct"], item["turnover"], 0)
        movers.append({
            "code": item["code"], "name": item["name"], "price": _format_price(item["price"]),
            "change": _format_change(item["change_pct"]), "volume": f"{item['turnover']:.1f}x",
            "sector": "全市场", "score": _score(item["change_pct"], item["turnover"], 0),
            "direction": "up" if item["change_pct"] >= 0 else "down",
            "signal": signal, "note": note, "risk": risk,
        })
    snapshot = {
        "as_of": now.isoformat(), "market_status": _market_status(now), "source": "sina",
        "is_live": _market_status(now) == "trading", "indices": fetch_indices(),
        "advancing": sum(row["change_pct"] > 0 for row in records),
        "declining": sum(row["change_pct"] < 0 for row in records),
        "northbound_flow": "--", "movers": movers,
        "sectors": [{"name": "全市场", "change": "--", "stocks": f"{sum(row['change_pct'] >= 0 for row in records)}/{len(records)}", "amount": _format_amount(sum(row["amount"] for row in records)), "direction": "up", "main_flow": "--", "twenty_day_change": "--", "pe": "--", "pb": "--"}],
    }
    bars = [{"captured_at": snapshot["as_of"], **item} for item in records]
    return snapshot, bars
