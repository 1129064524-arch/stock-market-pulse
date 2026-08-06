import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from math import ceil
from urllib.parse import urlencode
from urllib.request import Request
from zoneinfo import ZoneInfo

from api.network import open_url


EASTMONEY_HOST = "https://push2.eastmoney.com/api/qt"
EASTMONEY_USER_AGENT = "MarketPulse/0.1 (personal research tool)"
SHANGHAI = ZoneInfo("Asia/Shanghai")
STOCK_PAGE_SIZE = 100
MAX_PARALLEL_PAGES = 3


class MarketDataError(RuntimeError):
    """Raised when a market-data provider cannot produce a valid snapshot."""


def _get_json(path: str, params: dict) -> dict:
    url = f"{EASTMONEY_HOST}/{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": EASTMONEY_USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://quote.eastmoney.com/",
        },
    )
    last_error: Exception | None = None
    for delay in (0, 0.4, 1.0):
        if delay:
            time.sleep(delay)
        try:
            with open_url(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:  # Provider errors must not break the dashboard.
            last_error = error
    raise MarketDataError("Eastmoney market data is temporarily unavailable") from last_error


def _number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _format_price(value: object) -> str:
    return f"{_number(value):,.2f}"


def _format_change(value: object) -> str:
    change = _number(value)
    return f"{change:+.2f}%"


def _format_amount(value: object) -> str:
    amount = _number(value)
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.0f} 亿"
    if amount >= 10_000:
        return f"{amount / 10_000:.0f} 万"
    return f"{amount:.0f}"


def _format_flow(value: object) -> str:
    amount = _number(value)
    sign = "+" if amount > 0 else "" if amount == 0 else "-"
    absolute = abs(amount)
    if absolute >= 100_000_000:
        return f"{sign}{absolute / 100_000_000:.1f} 亿"
    if absolute >= 10_000:
        return f"{sign}{absolute / 10_000:.1f} 万"
    return f"{sign}{absolute:.0f}"


def _signal(change: float, turnover: float, main_flow: float) -> tuple[str, str, str]:
    if change >= 7 and turnover >= 5:
        return "放量突破", "涨幅和换手率同步放大", "短线乖离偏高"
    if main_flow > 0 and change >= 3:
        return "资金共振", "涨幅与主力净流入同步改善", "波动率可能上升"
    if change <= -4:
        return "风险异动", "跌幅明显扩大，需要确认承接", "趋势待确认"
    return "市场异动", "盘中价格与成交额出现变化", "等待更多信号确认"


def _score(change: float, turnover: float, main_flow: float) -> int:
    score = 50 + min(abs(change) * 4, 24) + min(turnover * 1.2, 14)
    if main_flow > 0:
        score += 8
    return max(35, min(98, round(score)))


def _market_status(now: datetime) -> str:
    local_time = now.astimezone(SHANGHAI)
    if local_time.weekday() >= 5:
        return "closed"
    minutes = local_time.hour * 60 + local_time.minute
    return "trading" if 570 <= minutes < 690 or 780 <= minutes < 900 else "closed"


def _collect_indices() -> list[dict]:
    data = _get_json(
        "ulist.np/get",
        {"fltt": "2", "invt": "2", "secids": "1.000001,0.399001,0.399006", "fields": "f12,f14,f2,f3"},
    )
    entries = data.get("data", {}).get("diff", [])
    if not entries:
        raise MarketDataError("Eastmoney index response was empty")
    return [
        {
            "name": item.get("f14", item.get("f12", "指数")),
            "value": _format_price(item.get("f2")),
            "change": _format_change(item.get("f3")),
            "direction": "up" if _number(item.get("f3")) >= 0 else "down",
        }
        for item in entries
    ]


def _collect_stock_page(page: int) -> tuple[int, list[dict]]:
    data = _get_json(
        "clist/get",
        {
            "pn": str(page),
            "pz": str(STOCK_PAGE_SIZE),
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": "f2,f3,f6,f7,f8,f12,f14,f62,f100",
        },
    )
    result = data.get("data", {})
    return int(result.get("total") or 0), result.get("diff", [])


def _collect_all_stocks() -> list[dict]:
    total, first_page = _collect_stock_page(1)
    if total <= 0 or not first_page:
        raise MarketDataError("Eastmoney stock response was empty")
    total_pages = ceil(total / STOCK_PAGE_SIZE)
    records = list(first_page)
    failures = 0
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_PAGES) as executor:
        futures = [executor.submit(_collect_stock_page, page) for page in range(2, total_pages + 1)]
        for future in as_completed(futures):
            try:
                _, page_records = future.result()
                records.extend(page_records)
            except MarketDataError:
                failures += 1
    if len(records) < total * 0.95:
        raise MarketDataError(f"Eastmoney collection incomplete ({len(records)}/{total}, failures={failures})")
    return records


def collect_eastmoney_overview() -> tuple[dict, list[dict]]:
    now = datetime.now(SHANGHAI)
    records = _collect_all_stocks()

    valid_records = [item for item in records if _number(item.get("f2")) > 0 and item.get("f12")]
    advancing = sum(_number(item.get("f3")) > 0 for item in valid_records)
    declining = sum(_number(item.get("f3")) < 0 for item in valid_records)
    selected_records = sorted(valid_records, key=lambda item: abs(_number(item.get("f3"))), reverse=True)[:12]

    movers = []
    for item in selected_records:
        change = _number(item.get("f3"))
        turnover = _number(item.get("f8"))
        main_flow = _number(item.get("f62"))
        signal, note, risk = _signal(change, turnover, main_flow)
        movers.append(
            {
                "code": str(item["f12"]),
                "name": str(item.get("f14") or item["f12"]),
                "price": _format_price(item.get("f2")),
                "change": _format_change(change),
                "volume": f"{turnover:.1f}x",
                "sector": str(item.get("f100") or "全市场"),
                "score": _score(change, turnover, main_flow),
                "direction": "up" if change >= 0 else "down",
                "signal": signal,
                "note": note,
                "risk": risk,
            }
        )

    industry_totals: dict[str, dict[str, float]] = {}
    for item in valid_records:
        industry = str(item.get("f100") or "其他")
        if industry == "其他":
            continue
        totals = industry_totals.setdefault(industry, {"change": 0, "amount": 0, "main_flow": 0, "up": 0, "count": 0})
        change = _number(item.get("f3"))
        totals["change"] += change
        totals["amount"] += _number(item.get("f6"))
        totals["main_flow"] += _number(item.get("f62"))
        totals["up"] += int(change > 0)
        totals["count"] += 1
    sectors = []
    for name, totals in sorted(industry_totals.items(), key=lambda pair: pair[1]["amount"], reverse=True)[:8]:
        average_change = totals["change"] / totals["count"]
        sectors.append(
            {
                "name": name,
                "change": _format_change(average_change),
                "stocks": f"{int(totals['up'])} / {int(totals['count'])}",
                "amount": _format_amount(totals["amount"]),
                "main_flow": _format_flow(totals["main_flow"]),
                "twenty_day_change": "--",
                "pe": "--",
                "pb": "--",
                "direction": "up" if average_change >= 0 else "down",
            }
        )

    snapshot = {
        "as_of": now.isoformat(),
        "market_status": _market_status(now),
        "source": "eastmoney",
        "is_live": _market_status(now) == "trading",
        "indices": _collect_indices(),
        "advancing": advancing,
        "declining": declining,
        "northbound_flow": "--",
        "movers": movers,
        "sectors": sectors,
    }
    bars = [
        {
            "captured_at": snapshot["as_of"],
            "code": str(item["f12"]),
            "name": str(item.get("f14") or item["f12"]),
            "price": _number(item.get("f2")),
            "change_pct": _number(item.get("f3")),
            "amount": _number(item.get("f6")),
            "turnover": _number(item.get("f8")),
            "industry": str(item.get("f100") or "全市场"),
            "source": "eastmoney",
        }
        for item in valid_records
    ]
    return snapshot, bars
