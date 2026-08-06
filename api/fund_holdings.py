"""Public fund-report holdings and transparent penetration calculations."""

import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request

from api.collector import MarketDataError, _number
from api.network import open_url
from api.storage import latest_fund_holdings, save_fund_holdings


HOLDINGS_URL = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


def parse_holdings_payload(text: str, report_date: str = "") -> list[dict]:
    """Parse the public holdings table without depending on BeautifulSoup."""
    # Eastmoney sometimes wraps the table in ``var apidata={content:"..."}``.
    # Decode that transport wrapper before feeding the HTML parser; direct HTML
    # responses continue through unchanged.
    wrapped = re.search(r"content\s*:\s*\"((?:\\.|[^\"])*)\"", text, re.S)
    if wrapped:
        try:
            text = json.loads(f'"{wrapped.group(1)}"')
        except json.JSONDecodeError:
            text = wrapped.group(1).replace('\\"', '"').replace('\\/', '/')
    parser = _TableParser()
    parser.feed(unescape(text))
    detected_date = report_date or next(iter(re.findall(r"20\d{2}-\d{2}-\d{2}", text)), "")
    holdings = []
    for row in parser.rows:
        code_index = next((index for index, value in enumerate(row) if re.fullmatch(r"\d{6}", value)), None)
        if code_index is None:
            continue
        code = row[code_index]
        name = row[code_index + 1] if code_index + 1 < len(row) else code
        weight = next((_number(value.replace("%", "")) for value in row[code_index + 2:] if re.fullmatch(r"\s*[-+]?\d+(?:\.\d+)?%?\s*", value)), 0.0)
        if weight <= 0:
            continue
        holdings.append({
            "stock_code": code,
            "stock_name": name,
            "weight_pct": weight,
            "report_date": detected_date or "unknown",
        })
    if not holdings:
        raise MarketDataError("Fund holdings response did not contain a usable table")
    return holdings[:10]


def fetch_fund_holdings(fund_code: str) -> list[dict]:
    if not re.fullmatch(r"\d{6}", fund_code):
        raise ValueError("Fund code must contain six digits")
    query = urlencode({"type": "jjcc", "code": fund_code, "topline": "10"})
    request = Request(
        f"{HOLDINGS_URL}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 MarketPulse/0.2",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Referer": f"https://fundf10.eastmoney.com/ccmx_{fund_code}.html",
        },
    )
    try:
        with open_url(request, timeout=15) as response:
            text = response.read().decode("utf-8", errors="replace")
        holdings = parse_holdings_payload(text)
        save_fund_holdings(fund_code, holdings)
        return holdings
    except ValueError:
        raise
    except Exception as error:
        cached = latest_fund_holdings(fund_code)
        if cached:
            return cached
        raise MarketDataError("Fund holdings are temporarily unavailable") from error


def calculate_holdings_pct(holdings: list[dict], stock_prices: dict[str, float]) -> dict:
    contributors = []
    for holding in holdings:
        change = stock_prices.get(str(holding["stock_code"]))
        if change is None:
            continue
        contribution = float(holding["weight_pct"]) * float(change) / 100
        contributors.append({
            "stock_code": holding["stock_code"],
            "stock_name": holding["stock_name"],
            "weight_pct": float(holding["weight_pct"]),
            "change_pct": float(change),
            "contribution": contribution,
        })
    contributors.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    return {
        "penetration_pct": sum(item["contribution"] for item in contributors),
        "contributors": contributors,
    }
