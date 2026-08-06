"""Optional AkShare adapter used as the preferred full-market source.

AkShare is deliberately imported inside the provider functions so the desktop
application remains usable when the optional package is not installed.
"""

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from api.collector import MarketDataError, _format_change, _format_price, _number

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _column(columns: dict[str, object], *names: str) -> object | None:
    return next((columns[name] for name in names if name in columns), None)


def normalize_stock_frame(frame: object) -> list[dict]:
    """Normalize AkShare's Chinese column names into the internal bar shape."""
    columns = {str(column): column for column in getattr(frame, "columns", [])}
    code_column = _column(columns, "代码", "code")
    name_column = _column(columns, "名称", "name")
    price_column = _column(columns, "最新价", "price")
    change_column = _column(columns, "涨跌幅", "change_pct")
    if not all((code_column, name_column, price_column, change_column)):
        raise MarketDataError("AkShare stock response has an unexpected schema")
    amount_column = _column(columns, "成交额", "amount")
    turnover_column = _column(columns, "换手率", "turnover")
    industry_column = _column(columns, "所属行业", "行业", "industry")
    records = []
    for row in frame.to_dict("records"):
        code = str(row.get(code_column) or "").strip().zfill(6)
        price = _number(row.get(price_column))
        if len(code) != 6 or price <= 0:
            continue
        records.append({
            "code": code,
            "name": str(row.get(name_column) or code),
            "price": price,
            "change_pct": _number(row.get(change_column)),
            "amount": _number(row.get(amount_column)) if amount_column else 0.0,
            "turnover": _number(row.get(turnover_column)) if turnover_column else 0.0,
            "industry": str(row.get(industry_column) or "全市场") if industry_column else "全市场",
            "source": "akshare",
        })
    if not records:
        raise MarketDataError("AkShare stock response was empty")
    return records


def fetch_stocks() -> list[dict]:
    try:
        import akshare as ak  # type: ignore[import-not-found]

        return normalize_stock_frame(ak.stock_zh_a_spot_em())
    except MarketDataError:
        raise
    except Exception as error:
        raise MarketDataError("AkShare is unavailable for full-market data") from error


def collect_overview() -> tuple[dict, list[dict]]:
    """Build the same snapshot contract as the Eastmoney collector."""
    from api.collector import _collect_indices_with_fallback, _format_amount, _format_flow, _market_status, _score, _signal

    records = fetch_stocks()
    now = datetime.now(SHANGHAI)
    movers = []
    for item in sorted(records, key=lambda row: abs(row["change_pct"]), reverse=True)[:12]:
        signal, note, risk = _signal(item["change_pct"], item["turnover"], 0)
        movers.append({
            "code": item["code"], "name": item["name"],
            "price": _format_price(item["price"]),
            "change": _format_change(item["change_pct"]),
            "volume": f"{item['turnover']:.1f}x",
            "sector": item["industry"], "score": _score(item["change_pct"], item["turnover"], 0),
            "direction": "up" if item["change_pct"] >= 0 else "down",
            "signal": signal, "note": note, "risk": risk,
        })

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in records:
        grouped[item["industry"]].append(item)
    sectors = []
    for name, items in sorted(grouped.items(), key=lambda pair: sum(row["amount"] for row in pair[1]), reverse=True)[:12]:
        avg_change = sum(row["change_pct"] for row in items) / len(items)
        amount = sum(row["amount"] for row in items)
        sectors.append({
            "name": name, "change": _format_change(avg_change),
            "stocks": f"{sum(row['change_pct'] >= 0 for row in items)}/{len(items)}",
            "amount": _format_amount(amount), "direction": "up" if avg_change >= 0 else "down",
            "main_flow": "--", "twenty_day_change": "--", "pe": "--", "pb": "--",
        })
    snapshot = {
        "as_of": now.isoformat(), "market_status": _market_status(now), "source": "akshare",
        "is_live": True, "indices": _collect_indices_with_fallback(),
        "advancing": sum(row["change_pct"] > 0 for row in records),
        "declining": sum(row["change_pct"] < 0 for row in records),
        "northbound_flow": "--", "movers": movers, "sectors": sectors,
    }
    bars = [{
        "captured_at": snapshot["as_of"], "code": item["code"], "name": item["name"],
        "price": item["price"], "change_pct": item["change_pct"], "amount": item["amount"],
        "turnover": item["turnover"], "industry": item["industry"], "source": "akshare",
    } for item in records]
    return snapshot, bars


def fetch_indices() -> list[dict]:
    try:
        import akshare as ak  # type: ignore[import-not-found]

        frame = ak.stock_zh_index_spot_em()
        columns = {str(column): column for column in frame.columns}
        name_column = columns.get("名称") or columns.get("name")
        value_column = columns.get("最新价") or columns.get("最新")
        change_column = columns.get("涨跌幅") or columns.get("涨跌")
        if not name_column or not value_column or not change_column:
            raise MarketDataError("AkShare index response has an unexpected schema")
        wanted = {"上证指数", "深证成指", "创业板指", "科创50"}
        result = []
        for row in frame.to_dict("records"):
            name = str(row.get(name_column) or "")
            if name not in wanted:
                continue
            change = _number(row.get(change_column))
            result.append({
                "name": name,
                "value": _format_price(row.get(value_column)),
                "change": _format_change(change),
                "direction": "up" if change >= 0 else "down",
            })
        if not result:
            raise MarketDataError("AkShare index response was empty")
        return result
    except MarketDataError:
        raise
    except Exception as error:
        raise MarketDataError("AkShare is unavailable for index data") from error
