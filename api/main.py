from datetime import datetime
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.collector import MarketDataError
from api.decision import build_decision_reference
from api.funds import latest_or_refresh as latest_funds_or_refresh
from api.llm import analyze_fund, analyze_market, analyze_signal, get_settings, public_settings, reset_settings, test_connection, update_settings
from api.indicators import summarize_bars, summarize_daily_bars
from api.linkage import build_cross_market_overview
from api.history import fetch_daily_bars
from api.fund_holdings import calculate_holdings_pct, fetch_fund_holdings
from api.market_service import is_trading_session, latest_or_refresh, refresh_and_persist
from api.models.fund import HoldingItem
from api.models.linkage import LinkedStock
from api.models.quote import Bar, MarketSnapshot, Mover, SectorStat, StockDetail, StockSummary
from api.models.signal import SignalEvent, SignalStats
from api.orchestrator import (
    LLMConfigurationError,
    LLMProviderError,
    auto_analysis_enabled,
    auto_analysis_interval_minutes,
    latest_cross_market_analysis,
    run_cross_market_analysis,
)
from api.rules import RULE_CATALOG, evaluate_rules, select_active_signals
from api.storage import daily_histories_for_codes, delete_watchlist_item, initialize, latest_analysis, list_watchlist, recent_analyses, recent_bars, recent_daily_bars, recent_signal_events, save_analysis, save_daily_bars, save_watchlist_item


class MarketIndex(BaseModel):
    name: str
    value: str
    change: str
    direction: Literal["up", "down"]


class MarketMover(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    price: str
    change: str
    volume: str
    sector: str
    score: int = Field(ge=0, le=100)
    direction: Literal["up", "down"]
    signal: str
    note: str
    risk: str


class SectorStrength(BaseModel):
    name: str
    change: str
    stocks: str
    amount: str
    direction: Literal["up", "down"]
    main_flow: str = "--"
    twenty_day_change: str = "--"
    pe: str = "--"
    pb: str = "--"


class FundQuote(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    fund_type: str
    theme: str
    nav: str
    estimate: str
    change: str
    week_change: str
    month_change: str
    quarter_change: str
    year_change: str
    direction: Literal["up", "down"]
    valuation_state: str
    nav_date: str
    signal: str
    risk: str
    source: Literal["eastmoney", "sample"]


class FundOverview(BaseModel):
    as_of: datetime
    source: Literal["eastmoney", "sample"]
    is_live: bool
    universe_count: int
    category_counts: dict[str, int]
    funds: list[FundQuote]


class LinkageItem(BaseModel):
    theme: str
    fund_count: int
    fund_change: str
    sector_change: str
    sectors: list[str]
    state: str
    confidence: int = Field(ge=0, le=100)
    note: str
    basis: str


class CrossMarketOverview(BaseModel):
    as_of: datetime
    stock_source: str
    fund_source: str
    stock_signal_count: int
    fund_signal_count: int
    items: list[LinkageItem]


class CrossMarketAnalysis(BaseModel):
    regime: Literal["股基共振", "股票偏强", "基金偏强", "同步偏弱", "明显分化", "中性观察"]
    summary: str = Field(max_length=240)
    stock_view: list[str] = Field(max_length=3)
    fund_view: list[str] = Field(max_length=3)
    linkages: list[dict[str, str]] = Field(max_length=6)
    divergences: list[str] = Field(max_length=3)
    next_checks: list[str] = Field(max_length=4)
    risks: list[str] = Field(max_length=3)
    disclaimer: str = Field(max_length=80)


class DecisionCard(BaseModel):
    theme: str
    day_change: str
    twenty_day_change: str
    pe: str
    pb: str
    main_flow: str
    decision: Literal["重点跟踪", "逢低核对", "持有观望", "风险收敛", "趋势观察"]
    analysis: str = Field(max_length=280)
    risk: str = Field(max_length=180)


class DecisionReference(BaseModel):
    as_of: datetime
    source: str
    analysis_source: Literal["llm", "rules"]
    cards: list[DecisionCard] = Field(max_length=8)
    disclaimer: str = Field(max_length=120)


class MarketOverview(BaseModel):
    as_of: datetime
    market_status: Literal["trading", "closed"]
    source: Literal["akshare", "eastmoney", "sina", "sample", "cache"]
    is_live: bool
    indices: list[MarketIndex]
    advancing: int
    declining: int
    northbound_flow: str
    movers: list[MarketMover]
    sectors: list[SectorStrength]


class WatchItem(BaseModel):
    code: str
    name: str
    reason: str


class WatchlistUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class WatchlistRecord(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    added_at: str


class MarketAnalysis(BaseModel):
    stance: Literal["偏强", "中性", "谨慎", "偏弱"]
    summary: str = Field(max_length=200)
    evidence: list[str] = Field(max_length=3)
    risks: list[str] = Field(max_length=3)
    watchlist: list[WatchItem] = Field(max_length=3)
    disclaimer: str


class FundAnalysis(BaseModel):
    summary: str = Field(max_length=240)
    evidence: list[str] = Field(max_length=3)
    risks: list[str] = Field(max_length=3)
    next_checks: list[str] = Field(max_length=3)
    disclaimer: str = Field(max_length=80)


class RuleSignal(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    rule_name: str
    rule_label: str
    rule_version: str
    score: int = Field(ge=0, le=100)
    evidence: str
    risk: str
    triggered_at: datetime
    source: str
    price: str
    change: str
    sector: str
    direction: Literal["up", "down"]
    volume: str


class SignalAnalysisRequest(BaseModel):
    signal: RuleSignal


class SignalResearch(BaseModel):
    summary: str = Field(max_length=240)
    why_now: list[str] = Field(max_length=3)
    confirmations: list[str] = Field(max_length=3)
    invalidations: list[str] = Field(max_length=3)
    next_session_checklist: list[str] = Field(max_length=3)
    risks: list[str] = Field(max_length=3)
    disclaimer: str = Field(max_length=80)


class LLMSettingsUpdate(BaseModel):
    base_url: str = Field(default="", max_length=500)
    endpoint: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=160)
    protocol: Literal["responses", "chat_completions"] = "chat_completions"
    timeout_seconds: float = Field(default=25, ge=5, le=180)
    auto_analysis_enabled: bool = False
    auto_analysis_minutes: int = Field(default=3, ge=1, le=60)


app = FastAPI(
    title="Market Pulse API",
    version="0.1.0",
    description="Local market-analysis API. The sample provider is replaceable with a licensed data feed.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4175", "http://localhost:4175", "http://127.0.0.1:4180", "http://localhost:4180"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


web_root_value = os.getenv("MARKET_PULSE_WEB_ROOT", "").strip()
WEB_ROOT = Path(web_root_value) if web_root_value else None
if WEB_ROOT and WEB_ROOT.is_dir():
    app.mount("/app", StaticFiles(directory=WEB_ROOT, html=True), name="desktop-app")


@app.on_event("startup")
def prepare_storage() -> None:
    initialize()


def sample_overview() -> MarketOverview:
    return MarketOverview(
        as_of=datetime.now().astimezone(),
        market_status="trading" if is_trading_session() else "closed",
        source="sample",
        is_live=False,
        indices=[
            {"name": "上证指数", "value": "3,421.36", "change": "+0.68%", "direction": "up"},
            {"name": "深证成指", "value": "10,824.19", "change": "+1.12%", "direction": "up"},
            {"name": "创业板指", "value": "2,241.80", "change": "+1.84%", "direction": "up"},
        ],
        advancing=3681,
        declining=1426,
        northbound_flow="+42.8 亿",
        movers=[
            {"code": "300308", "name": "中际旭创", "price": "184.62", "change": "+8.41%", "volume": "3.8x", "sector": "通信设备", "score": 91, "direction": "up", "signal": "放量突破", "note": "突破 20 日高点，所属板块同步走强", "risk": "短线乖离偏高"},
            {"code": "688256", "name": "寒武纪-U", "price": "612.80", "change": "+6.73%", "volume": "2.9x", "sector": "半导体", "score": 87, "direction": "up", "signal": "资金共振", "note": "主力净流入连续 3 个交易日", "risk": "波动率高于均值"},
            {"code": "002230", "name": "科大讯飞", "price": "54.36", "change": "+5.18%", "volume": "2.4x", "sector": "AI 应用", "score": 84, "direction": "up", "signal": "趋势转强", "note": "5 日线上穿 20 日线，板块排名提升", "risk": "上方年线压力"},
            {"code": "601127", "name": "赛力斯", "price": "118.40", "change": "-4.26%", "volume": "2.1x", "sector": "汽车整车", "score": 79, "direction": "down", "signal": "高位放量", "note": "跌破短期均线，资金流出加速", "risk": "趋势待确认"},
            {"code": "159995", "name": "芯片 ETF", "price": "1.142", "change": "+2.34%", "volume": "1.8x", "sector": "ETF", "score": 75, "direction": "up", "signal": "板块转强", "note": "半导体成交额升至全市场第 3", "risk": "受龙头波动影响"},
            {"code": "600519", "name": "贵州茅台", "price": "1518.21", "change": "-1.64%", "volume": "1.5x", "sector": "白酒", "score": 62, "direction": "down", "signal": "资金背离", "note": "指数反弹但个股资金持续流出", "risk": "防御板块承压"},
        ],
        sectors=[
            {"name": "通信设备", "change": "+4.82%", "stocks": "18 / 42", "amount": "284 亿", "direction": "up"},
            {"name": "半导体", "change": "+3.67%", "stocks": "96 / 174", "amount": "516 亿", "direction": "up"},
            {"name": "AI 应用", "change": "+2.91%", "stocks": "73 / 126", "amount": "193 亿", "direction": "up"},
            {"name": "汽车整车", "change": "-1.22%", "stocks": "8 / 31", "amount": "98 亿", "direction": "down"},
        ],
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _v1_number(value: object) -> float:
    """Parse the display-oriented values used by the legacy API models."""
    try:
        return float(str(value or "0").replace(",", "").replace("%", "").replace("亿", ""))
    except (TypeError, ValueError):
        return 0.0


def _v1_summary(bar: dict) -> StockSummary:
    return StockSummary(
        code=str(bar["code"]),
        name=str(bar.get("name") or bar["code"]),
        price=float(bar.get("price") or 0),
        change_pct=float(bar.get("change_pct") or 0),
        amount=float(bar.get("amount") or 0),
        turnover=float(bar.get("turnover") or 0),
        sector=str(bar.get("industry") or "全市场"),
    )


@app.get("/api/v1/system/health")
def v1_health() -> dict[str, str]:
    return health()


@app.get("/api/v1/watchlist/{asset_type}", response_model=list[WatchlistRecord])
def v1_watchlist(asset_type: Literal["stock", "fund"]) -> list[WatchlistRecord]:
    return [WatchlistRecord.model_validate(item) for item in list_watchlist(asset_type)]


@app.put("/api/v1/watchlist/{asset_type}/{code}", response_model=WatchlistRecord)
def v1_save_watchlist(asset_type: Literal["stock", "fund"], code: str, request: WatchlistUpdate) -> WatchlistRecord:
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=422, detail="代码必须是 6 位数字")
    return WatchlistRecord.model_validate(save_watchlist_item(asset_type, code, request.name.strip()))


@app.delete("/api/v1/watchlist/{asset_type}/{code}", status_code=204)
def v1_delete_watchlist(asset_type: Literal["stock", "fund"], code: str) -> None:
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=422, detail="代码必须是 6 位数字")
    delete_watchlist_item(asset_type, code)


@app.get("/api/v1/market/snapshot", response_model=MarketSnapshot)
def v1_market_snapshot() -> MarketSnapshot:
    snapshot = market_overview()
    indices = {index.name: _v1_number(index.value) for index in snapshot.indices}
    bars = recent_bars_for_snapshot(snapshot.model_dump(mode="json"))
    return MarketSnapshot(
        captured_at=snapshot.as_of.isoformat(),
        indices=indices,
        total_amount=sum(float(bar.get("amount") or 0) for bar in bars),
        up_count=snapshot.advancing,
        down_count=snapshot.declining,
    )


@app.get("/api/v1/market/stocks", response_model=list[StockSummary])
def v1_market_stocks() -> list[StockSummary]:
    snapshot = market_overview()
    bars = recent_bars_for_snapshot(snapshot.model_dump(mode="json"))
    if bars:
        return [_v1_summary(bar) for bar in bars]
    return [
        StockSummary(
            code=mover.code,
            name=mover.name,
            price=_v1_number(mover.price),
            change_pct=_v1_number(mover.change),
            sector=mover.sector,
        )
        for mover in snapshot.movers
    ]


@app.get("/api/v1/market/stocks/{code}", response_model=StockDetail)
def v1_stock_detail(code: str) -> StockDetail:
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=422, detail="股票代码必须是 6 位数字")
    snapshot = market_overview()
    bars = [bar for bar in recent_bars_for_snapshot(snapshot.model_dump(mode="json")) if bar["code"] == code]
    if bars:
        return StockDetail(**_v1_summary(bars[-1]).model_dump())
    mover = next((item for item in snapshot.movers if item.code == code), None)
    if mover is None:
        raise HTTPException(status_code=404, detail="当前快照没有该股票")
    return StockDetail(
        code=code,
        name=mover.name,
        price=_v1_number(mover.price),
        change_pct=_v1_number(mover.change),
        sector=mover.sector,
    )


@app.get("/api/v1/market/stocks/{code}/bars", response_model=list[Bar])
def v1_stock_bars(code: str, days: int = 60) -> list[Bar]:
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=422, detail="股票代码必须是 6 位数字")
    bars = recent_daily_bars(code, min(max(days, 1), 1000))
    return [
        Bar(
            date=str(bar["trading_date"]),
            open=float(bar["open"]),
            high=float(bar["high"]),
            low=float(bar["low"]),
            close=float(bar["close"]),
            volume=float(bar["volume"]),
            amount=float(bar["amount"]),
        )
        for bar in bars
    ]


@app.get("/api/v1/market/sectors", response_model=list[SectorStat])
def v1_market_sectors() -> list[SectorStat]:
    snapshot = market_overview()
    result = []
    for sector in snapshot.sectors:
        parts = sector.stocks.split("/", 1)
        up_count = int(_v1_number(parts[0])) if parts else 0
        stock_count = int(_v1_number(parts[1])) if len(parts) > 1 else 0
        result.append(SectorStat(
            name=sector.name,
            avg_pct=_v1_number(sector.change),
            up_ratio=up_count / stock_count if stock_count else 0,
            stock_count=stock_count,
        ))
    return result


@app.get("/api/v1/market/movers", response_model=list[Mover])
def v1_market_movers() -> list[Mover]:
    snapshot = market_overview()
    return [Mover(
        code=item.code,
        name=item.name,
        price=_v1_number(item.price),
        change_pct=_v1_number(item.change),
        reason=item.signal,
    ) for item in snapshot.movers]


@app.get("/api/v1/funds/{code}/holdings", response_model=list[HoldingItem])
def v1_fund_holdings(code: str) -> list[HoldingItem]:
    try:
        return [HoldingItem.model_validate(item) for item in fetch_fund_holdings(code)]
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except MarketDataError as error:
        raise HTTPException(status_code=502, detail={"code": "fund_holdings_unavailable", "message": str(error)}) from error


@app.get("/api/v1/linkage/fund/{code}/stocks", response_model=list[LinkedStock])
def v1_fund_linked_stocks(code: str) -> list[LinkedStock]:
    holdings = [item.model_dump() for item in v1_fund_holdings(code)]
    snapshot = market_overview()
    bars = recent_bars_for_snapshot(snapshot.model_dump(mode="json"))
    stock_prices = {str(bar["code"]): float(bar.get("change_pct") or 0) for bar in bars}
    penetration = calculate_holdings_pct(holdings, stock_prices)
    return [
        LinkedStock(
            code=item["stock_code"],
            name=item["stock_name"],
            weight_pct=item["weight_pct"],
            change_pct=item["change_pct"],
            contribution=item["contribution"],
        )
        for item in penetration["contributors"]
    ]


@app.get("/api/market/overview", response_model=MarketOverview)
def market_overview() -> MarketOverview:
    """Return a fresh cached snapshot, refreshing the provider when necessary."""
    snapshot = latest_or_refresh(max_age_seconds=90)
    return MarketOverview.model_validate(snapshot) if snapshot is not None else sample_overview()


@app.post("/api/market/refresh", response_model=MarketOverview)
def refresh_market_snapshot() -> MarketOverview:
    """Fetch and persist a new all-market snapshot, with cached or sample fallback."""
    try:
        snapshot = refresh_and_persist()
        return MarketOverview.model_validate(snapshot)
    except Exception:
        fallback = latest_or_refresh(max_age_seconds=10**9)
        if fallback is not None:
            # A stale snapshot is useful for continuity, but must never be
            # presented as a live provider response after a failed refresh.
            fallback["source"] = "cache"
            fallback["is_live"] = False
            fallback["market_status"] = "trading" if is_trading_session() else "closed"
            return MarketOverview.model_validate(fallback)
        return sample_overview()


@app.get("/api/funds/overview", response_model=FundOverview)
def funds_overview() -> FundOverview:
    """Return cached fund estimates and latest confirmed NAV references."""
    return FundOverview.model_validate(latest_funds_or_refresh())


@app.post("/api/funds/refresh", response_model=FundOverview)
def refresh_funds_snapshot() -> FundOverview:
    """Refresh the configured fund watchlist without exposing any trade action."""
    from api.funds import collect_fund_overview

    return FundOverview.model_validate(collect_fund_overview())


@app.get("/api/linkage/overview", response_model=CrossMarketOverview)
def linkage_overview() -> CrossMarketOverview:
    """Coordinate stock-sector signals with fund style changes without implying holdings certainty."""
    market = market_overview().model_dump(mode="json")
    funds = FundOverview.model_validate(latest_funds_or_refresh()).model_dump(mode="json")
    return CrossMarketOverview.model_validate(build_cross_market_overview(market, funds))


@app.post("/api/analysis/cross-market", response_model=CrossMarketAnalysis)
def cross_market_analysis() -> CrossMarketAnalysis:
    """Let the configured model coordinate bounded stock, fund and linkage evidence."""
    try:
        return CrossMarketAnalysis.model_validate(run_cross_market_analysis())
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail={"code": "llm_not_configured", "message": "请在 .env 中配置兼容模型通道后再生成跨市场研判。"}) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail={"code": "llm_provider_error", "message": "模型服务暂时不可用，请检查共享 API 通道和网络。"}) from error


@app.post("/api/analysis/decision-reference", response_model=DecisionReference)
def decision_reference() -> DecisionReference:
    """Return API-generated sector research cards, with a deterministic fallback when the model is unavailable."""
    return DecisionReference.model_validate(build_decision_reference())


@app.get("/api/analysis/cross-market/latest", response_model=CrossMarketAnalysis)
def latest_cross_market() -> CrossMarketAnalysis:
    result = latest_cross_market_analysis()
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "analysis_not_ready", "message": "尚未生成跨市场研判。"})
    return CrossMarketAnalysis.model_validate(result)


@app.get("/api/stocks/{code}/bars")
def stock_bars(code: str, limit: int = 240) -> dict[str, object]:
    bars = recent_bars(code, min(max(limit, 1), 1000))
    return {"code": code, "bars": bars, "indicators": summarize_bars(bars)}


@app.get("/api/stocks/{code}/daily-bars")
def stock_daily_bars(code: str, limit: int = 250) -> dict[str, object]:
    bars = recent_daily_bars(code, min(max(limit, 1), 1000))
    return {"code": code, "bars": bars, "indicators": summarize_daily_bars(bars)}


@app.post("/api/stocks/{code}/daily-history")
def refresh_stock_daily_history(code: str, limit: int = 250) -> dict[str, object]:
    try:
        bars = fetch_daily_bars(code, limit)
        save_daily_bars(bars)
        return {"code": code, "source": "eastmoney", "bars": bars}
    except (ValueError, MarketDataError) as error:
        raise HTTPException(status_code=502, detail={"code": "daily_history_unavailable", "message": str(error)}) from error


@app.get("/api/signals/history")
def signal_history(limit: int = 100) -> dict[str, object]:
    return {"events": recent_signal_events(min(max(limit, 1), 500))}


@app.get("/api/rules/catalog")
def rules_catalog() -> dict[str, object]:
    return {"rules": RULE_CATALOG}


@app.get("/api/signals/current", response_model=list[RuleSignal])
def current_signals(limit: int = 160) -> list[RuleSignal]:
    """Return a balanced, bounded scan queue from the complete rule output."""
    snapshot = latest_or_refresh(max_age_seconds=90)
    if snapshot is None:
        return []
    bars = recent_bars_for_snapshot(snapshot)
    if not bars:
        return []
    histories = daily_histories_for_codes([bar["code"] for bar in bars])
    signals = evaluate_rules(bars, histories)
    return [RuleSignal.model_validate(signal) for signal in select_active_signals(signals, limit)]


def _v1_signal(signal: RuleSignal) -> SignalEvent:
    return SignalEvent(
        code=signal.code,
        name=signal.name,
        rule_name=signal.rule_name,
        rule_version=signal.rule_version,
        score=signal.score,
        direction="bullish" if signal.direction == "up" else "bearish",
        evidence={"text": signal.evidence, "price": signal.price, "change": signal.change},
        risk_note=signal.risk,
        triggered_at=signal.triggered_at.isoformat(),
    )


@app.get("/api/v1/signals/latest", response_model=list[SignalEvent])
def v1_latest_signals(limit: int = 50) -> list[SignalEvent]:
    return [_v1_signal(signal) for signal in current_signals(min(max(limit, 1), 300))]


@app.get("/api/v1/signals/history", response_model=list[SignalEvent])
def v1_signal_history(limit: int = 100, date: str | None = None) -> list[SignalEvent]:
    """Return persisted, cooldown-deduplicated signals for audit and review."""
    if date and (len(date) != 10 or date[4] != "-" or date[7] != "-"):
        raise HTTPException(status_code=422, detail="date 必须使用 YYYY-MM-DD 格式")
    events = recent_signal_events(min(max(limit, 1), 500), date=date)
    return [SignalEvent(
        code=str(event["code"]),
        name=event["name"],
        rule_name=event["rule_name"],
        rule_version=event.get("rule_version") or "legacy",
        score=float(event["score"]),
        direction=event.get("direction") or "unknown",
        evidence={"text": event["evidence"], "source": event["source"]},
        risk_note=event["risk"],
        triggered_at=event["triggered_at"],
    ) for event in events]


@app.get("/api/v1/signals/stats", response_model=SignalStats)
def v1_signal_stats() -> SignalStats:
    signals = v1_latest_signals(300)
    rule_counts: dict[str, int] = {}
    for signal in signals:
        rule_counts[signal.rule_name] = rule_counts.get(signal.rule_name, 0) + 1
    top_rules = [
        {"rule": rule, "count": count}
        for rule, count in sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return SignalStats(
        total_today=len(signals),
        bullish_count=sum(signal.direction == "bullish" for signal in signals),
        bearish_count=sum(signal.direction == "bearish" for signal in signals),
        top_rules=top_rules,
    )


def recent_bars_for_snapshot(snapshot: dict) -> list[dict]:
    """All-market bars are stored under the snapshot timestamp, not per stock request."""
    from api.storage import snapshot_bars

    return snapshot_bars(snapshot["as_of"])


@app.get("/api/llm/status")
def llm_status() -> dict[str, bool | str | int]:
    settings = get_settings()
    return {
        "configured": settings.configured,
        "protocol": settings.protocol,
        "auto_analysis_enabled": auto_analysis_enabled(),
        "auto_analysis_minutes": auto_analysis_interval_minutes(),
    }


@app.get("/api/llm/settings")
def llm_settings() -> dict[str, object]:
    return public_settings()


@app.put("/api/llm/settings")
def save_llm_settings(request: LLMSettingsUpdate) -> dict[str, object]:
    try:
        return update_settings(request.model_dump())
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail={"code": "llm_settings_invalid", "message": str(error)}) from error


@app.delete("/api/llm/settings")
def clear_llm_settings() -> dict[str, object]:
    return reset_settings()


@app.post("/api/llm/test")
def test_llm() -> dict[str, object]:
    try:
        return test_connection()
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail={"code": "llm_not_configured", "message": "请先保存完整的模型通道配置。"}) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail={"code": "llm_provider_error", "message": "模型连接失败，请检查地址、密钥、模型和网络。"}) from error


@app.post("/api/analysis/market", response_model=MarketAnalysis)
def market_analysis() -> MarketAnalysis:
    """Ask the configured model to explain the current normalized market snapshot."""
    snapshot = market_overview().model_dump(mode="json")
    try:
        return MarketAnalysis.model_validate(analyze_market(snapshot))
    except LLMConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "llm_not_configured", "message": "请在 .env 中配置兼容模型的地址、密钥和模型名称。"},
        ) from error
    except LLMProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "llm_provider_error", "message": "模型服务暂时不可用，请检查地址、密钥、模型名称和网络。"},
        ) from error


@app.post("/api/v1/analysis/funds/{code}", response_model=FundAnalysis)
def fund_analysis(code: str) -> FundAnalysis:
    """Analyze one fund from its quote, report holdings and local contributions."""
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=422, detail="基金代码必须是 6 位数字")
    overview = FundOverview.model_validate(latest_funds_or_refresh()).model_dump(mode="json")
    fund = next((item for item in overview["funds"] if item["code"] == code), None)
    if fund is None:
        raise HTTPException(status_code=404, detail="当前基金快照没有该基金")
    holdings = [item.model_dump() for item in v1_fund_holdings(code)]
    snapshot = market_overview()
    bars = recent_bars_for_snapshot(snapshot.model_dump(mode="json"))
    stock_prices = {str(bar["code"]): float(bar.get("change_pct") or 0) for bar in bars}
    penetration = calculate_holdings_pct(holdings, stock_prices)
    context = {
        "as_of": overview["as_of"],
        "fund": fund,
        "holdings": holdings,
        "penetration": penetration,
        "market": {"as_of": snapshot.as_of.isoformat(), "source": snapshot.source, "indices": [item.model_dump() for item in snapshot.indices]},
    }
    try:
        result = FundAnalysis.model_validate(analyze_fund(context))
        save_analysis(f"fund:{code}", result.model_dump())
        return result
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail={"code": "llm_not_configured", "message": "请先在设置中配置模型通道。"}) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail={"code": "llm_provider_error", "message": "模型服务暂时不可用，请检查通道配置。"}) from error


@app.get("/api/v1/analysis/funds/{code}/latest", response_model=FundAnalysis)
def latest_fund_analysis(code: str) -> FundAnalysis:
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=422, detail="基金代码必须是 6 位数字")
    result = latest_analysis(f"fund:{code}")
    if result is None:
        raise HTTPException(status_code=404, detail="该基金尚未生成研判")
    return FundAnalysis.model_validate(result)


@app.get("/api/v1/analysis/history", response_model=list[dict[str, object]])
def analysis_history(kind: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    allowed = {"market", "cross_market", "cross-market", "decision_reference"}
    if kind and not (kind in allowed or kind.startswith("fund:")):
        raise HTTPException(status_code=422, detail="不支持的研判类型")
    return recent_analyses(kind, min(max(limit, 1), 100))
@app.post("/api/analysis/signals", response_model=SignalResearch)
def signal_analysis(request: SignalAnalysisRequest) -> SignalResearch:
    """Generate a bounded research checklist for one selected, explainable rule signal."""
    overview = market_overview().model_dump(mode="json")
    signal = request.signal.model_dump(mode="json")
    context = {
        "signal": signal,
        "market_context": {
            key: overview.get(key)
            for key in ("as_of", "market_status", "source", "is_live", "indices", "advancing", "declining", "sectors")
        },
        "local_daily_history": recent_daily_bars(signal["code"], 60),
    }
    try:
        return SignalResearch.model_validate(analyze_signal(context))
    except LLMConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "llm_not_configured", "message": "请在 .env 中配置兼容模型的地址、密钥和模型名称。"},
        ) from error
    except LLMProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "llm_provider_error", "message": "模型服务暂时不可用，请检查地址、密钥、模型名称和网络。"},
        ) from error
