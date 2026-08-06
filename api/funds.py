import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request
from zoneinfo import ZoneInfo

from api.collector import MarketDataError, _number
from api.network import open_url


RANKING_URL = "https://fund.eastmoney.com/data/rankhandler.aspx"
FUND_DIRECTORY_URL = "https://fund.eastmoney.com/js/fundcode_search.js"
SHANGHAI = ZoneInfo("Asia/Shanghai")
_cache: dict | None = None
_cache_at = 0.0


SAMPLE_FUNDS = [
    {"code": "002910", "name": "易方达供给改革混合", "fund_type": "混合型-偏股", "nav": "8.364", "change": "+3.69%", "week_change": "+3.83%", "month_change": "+2.74%", "quarter_change": "+66.49%", "year_change": "+204.92%"},
    {"code": "001480", "name": "财通成长优选混合 A", "fund_type": "混合型-偏股", "nav": "7.147", "change": "+4.41%", "week_change": "+10.21%", "month_change": "-22.31%", "quarter_change": "+25.34%", "year_change": "+201.94%"},
    {"code": "018777", "name": "金信精选成长混合 C", "fund_type": "混合型-偏股", "nav": "2.361", "change": "+9.69%", "week_change": "+4.08%", "month_change": "-23.95%", "quarter_change": "+10.55%", "year_change": "+87.81%"},
    {"code": "011593", "name": "农银汇理安瑞一年持有混合 FOF", "fund_type": "FOF", "nav": "0.860", "change": "-3.50%", "week_change": "-12.72%", "month_change": "-22.28%", "quarter_change": "-11.32%", "year_change": "+14.70%"},
    {"code": "019245", "name": "鹏华易诚积极三个月持有混合 FOF A", "fund_type": "FOF", "nav": "1.675", "change": "-2.20%", "week_change": "-5.39%", "month_change": "-9.89%", "quarter_change": "-0.30%", "year_change": "+30.92%"},
    {"code": "003095", "name": "中欧医疗健康混合 A", "fund_type": "混合型-偏股", "nav": "1.264", "change": "-1.03%", "week_change": "-2.10%", "month_change": "+1.24%", "quarter_change": "+3.66%", "year_change": "+8.42%"},
]


def _request_text(url: str, referer: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MarketPulse/0.2",
            "Accept": "text/javascript,application/javascript,text/plain,*/*",
            "Referer": referer,
        },
    )
    try:
        with open_url(request, timeout=15) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    except Exception as error:
        raise MarketDataError("Eastmoney fund market data is temporarily unavailable") from error


def _change_text(value: object) -> str:
    if value in (None, "", "--"):
        return "--"
    return f"{_number(value):+.2f}%"


def _theme_for(name: str, fund_type: str) -> str:
    checks = (
        (("半导体", "芯片", "集成电路"), "半导体"),
        (("医药", "医疗", "生物", "创新药"), "医药医疗"),
        (("消费", "白酒", "食品", "家电"), "消费"),
        (("人工智能", "AI", "数字经济", "计算机"), "科技成长"),
        (("新能源", "光伏", "电池", "汽车"), "新能源"),
        (("军工", "国防"), "国防军工"),
        (("港股", "恒生"), "港股"),
        (("纳指", "标普", "美国", "全球"), "海外权益"),
        (("债券", "纯债", "信用债", "可转债"), "固收"),
    )
    for keywords, theme in checks:
        if any(keyword.lower() in name.lower() for keyword in keywords):
            return theme
    if "指数" in fund_type:
        return "宽基 / 指数"
    if "FOF" in fund_type.upper():
        return "多资产"
    return fund_type.split("-")[0] if fund_type else "未分类"


def _signal_for(change: float) -> tuple[str, str]:
    if change >= 5:
        return "强势异动", "涨幅显著，需核对净值日期与集中暴露"
    if change >= 2:
        return "趋势改善", "短期涨幅扩大，观察持续性"
    if change <= -3:
        return "下行异动", "净值跌幅较大，确认风格和重仓风险"
    if change <= -1:
        return "弱势观察", "短期承压，等待净值与市场同步确认"
    return "常态波动", "单日变化处于常态区间"


def parse_directory_payload(text: str) -> dict[str, str]:
    match = re.search(r"var\s+r\s*=\s*(\[.*\]);?\s*$", text.strip(), re.S)
    if match is None:
        raise MarketDataError("Fund directory response was invalid")
    rows = json.loads(match.group(1))
    return {str(row[0]): str(row[3]) for row in rows if isinstance(row, list) and len(row) >= 4}


def parse_rank_payload(text: str, fund_types: dict[str, str] | None = None) -> tuple[list[dict], int, dict[str, int]]:
    match = re.search(r"datas:(\[.*?\]),allRecords:(\d+)", text, re.S)
    if match is None:
        raise MarketDataError("Fund ranking response was invalid")
    rows = json.loads(match.group(1))
    types = fund_types or {}
    funds = []
    for row in rows:
        parts = row.split(",")
        if len(parts) < 17:
            continue
        change = _number(parts[6])
        signal, risk = _signal_for(change)
        fund_type = types.get(parts[0], "未分类")
        funds.append({
            "code": parts[0],
            "name": parts[1],
            "fund_type": fund_type,
            "theme": _theme_for(parts[1], fund_type),
            "nav": f"{_number(parts[4]):.4f}",
            "estimate": f"{_number(parts[4]):.4f}",
            "change": _change_text(parts[6]),
            "week_change": _change_text(parts[7]),
            "month_change": _change_text(parts[8]),
            "quarter_change": _change_text(parts[9]),
            "year_change": _change_text(parts[11]),
            "direction": "up" if change >= 0 else "down",
            "valuation_state": "确认净值",
            "nav_date": parts[3],
            "signal": signal,
            "risk": risk,
            "source": "eastmoney",
        })
    counts = {
        "指数型": int(re.search(r"zs_count:(\d+)", text).group(1)) if re.search(r"zs_count:(\d+)", text) else 0,
        "股票型": int(re.search(r"gp_count:(\d+)", text).group(1)) if re.search(r"gp_count:(\d+)", text) else 0,
        "混合型": int(re.search(r"hh_count:(\d+)", text).group(1)) if re.search(r"hh_count:(\d+)", text) else 0,
        "债券型": int(re.search(r"zq_count:(\d+)", text).group(1)) if re.search(r"zq_count:(\d+)", text) else 0,
        "QDII": int(re.search(r"qdii_count:(\d+)", text).group(1)) if re.search(r"qdii_count:(\d+)", text) else 0,
        "FOF": int(re.search(r"fof_count:(\d+)", text).group(1)) if re.search(r"fof_count:(\d+)", text) else 0,
    }
    return funds, int(match.group(2)), counts


def _ranking_url(order: str, limit: int) -> str:
    today = datetime.now(SHANGHAI).date()
    params = {
        "op": "ph", "dt": "kf", "ft": "all", "rs": "", "gs": "0", "sc": "rzdf", "st": order,
        "sd": str(today - timedelta(days=365)), "ed": str(today), "qdii": "", "tabSubtype": ",,,,,",
        "pi": "1", "pn": str(limit), "dx": "1", "v": str(time.time()),
    }
    return f"{RANKING_URL}?{urlencode(params)}"


def _sample_overview() -> dict:
    funds = []
    for item in SAMPLE_FUNDS:
        change = _number(item["change"].rstrip("%"))
        signal, risk = _signal_for(change)
        funds.append({
            **item,
            "theme": _theme_for(item["name"], item["fund_type"]),
            "estimate": item["nav"],
            "direction": "up" if change >= 0 else "down",
            "valuation_state": "演示净值",
            "nav_date": "演示日期",
            "signal": signal,
            "risk": risk,
            "source": "sample",
        })
    return {
        "as_of": datetime.now(SHANGHAI).isoformat(), "source": "sample", "is_live": False,
        "universe_count": 0, "category_counts": {}, "funds": funds,
    }


def collect_fund_overview() -> dict:
    global _cache, _cache_at
    limit = min(max(int(os.getenv("FUND_SCAN_LIMIT", "30")), 10), 100)
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            directory_future = executor.submit(_request_text, FUND_DIRECTORY_URL, "https://fund.eastmoney.com/")
            top_future = executor.submit(_request_text, _ranking_url("desc", limit), "https://fund.eastmoney.com/data/fundranking.html")
            bottom_future = executor.submit(_request_text, _ranking_url("asc", limit), "https://fund.eastmoney.com/data/fundranking.html")
            fund_types = parse_directory_payload(directory_future.result())
            top_funds, universe_count, category_counts = parse_rank_payload(top_future.result(), fund_types)
            bottom_funds, _, _ = parse_rank_payload(bottom_future.result(), fund_types)
        seen = set()
        funds = []
        for item in top_funds + bottom_funds:
            if item["code"] not in seen:
                seen.add(item["code"])
                funds.append(item)
        overview = {
            "as_of": datetime.now(SHANGHAI).isoformat(), "source": "eastmoney", "is_live": False,
            "universe_count": universe_count, "category_counts": category_counts, "funds": funds,
        }
    except (MarketDataError, ValueError, json.JSONDecodeError):
        overview = _sample_overview()
    _cache, _cache_at = overview, time.monotonic()
    return overview


def latest_or_refresh(max_age_seconds: int = 300) -> dict:
    if _cache is not None and time.monotonic() - _cache_at < max_age_seconds:
        return _cache
    return collect_fund_overview()
