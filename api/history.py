import json
from urllib.parse import urlencode
from urllib.request import Request

from api.collector import EASTMONEY_USER_AGENT, MarketDataError, _number
from api.network import open_url


HISTORY_HOST = "https://push2his.eastmoney.com/api/qt"


def secid_for_a_share(code: str) -> str:
    if not code.isdigit() or len(code) != 6:
        raise ValueError("A-share code must contain six digits")
    market = "1" if code.startswith(("5", "6", "9")) else "0"
    return f"{market}.{code}"


def fetch_daily_bars(code: str, limit: int = 250) -> list[dict]:
    safe_limit = min(max(limit, 1), 1000)
    query = urlencode(
        {
            "secid": secid_for_a_share(code),
            "klt": "101",
            "fqt": "1",
            "lmt": str(safe_limit),
            "end": "20500101",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
    )
    request = Request(
        f"{HISTORY_HOST}/stock/kline/get?{query}",
        headers={"User-Agent": EASTMONEY_USER_AGENT, "Accept": "application/json", "Referer": "https://quote.eastmoney.com/"},
    )
    try:
        with open_url(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise MarketDataError("Eastmoney daily history is temporarily unavailable") from error
    rows = payload.get("data", {}).get("klines", [])
    bars = []
    for row in rows:
        parts = row.split(",")
        if len(parts) < 11:
            continue
        bars.append(
            {
                "code": code,
                "trading_date": parts[0],
                "open": _number(parts[1]),
                "close": _number(parts[2]),
                "high": _number(parts[3]),
                "low": _number(parts[4]),
                "volume": _number(parts[5]),
                "amount": _number(parts[6]),
                "change_pct": _number(parts[8]),
                "turnover": _number(parts[10]),
                "source": "eastmoney",
            }
        )
    if not bars:
        raise MarketDataError("Eastmoney daily history response was empty")
    return bars
