"""Evidence manifests for bounded, auditable model research.

The LLM still writes the research narrative.  This layer attaches the exact
local snapshots available for that run and rejects references outside them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _as_of(value: object) -> str:
    return str(value or datetime.now().astimezone().isoformat())


def _item(identifier: str, title: str, source: object, as_of: object, path: str, value: Any, *, caveat: str = "") -> dict[str, Any]:
    return {
        "id": identifier,
        "title": title,
        "source": str(source or "local"),
        "as_of": _as_of(as_of),
        "path": path,
        "value": value,
        "caveat": caveat,
    }


def _bundle(scope: str, items: list[dict[str, Any]], limitations: list[str]) -> dict[str, Any]:
    unique_sources = list(dict.fromkeys(item["source"] for item in items))
    return {
        "scope": scope,
        "manifest": items,
        "coverage": {
            "status": "limited" if limitations else "verified",
            "item_count": len(items),
            "sources": unique_sources,
            "as_of": max((item["as_of"] for item in items), default=""),
            "limitations": limitations,
        },
    }


def market_bundle(snapshot: dict[str, Any]) -> dict[str, Any]:
    source, as_of = snapshot.get("source"), snapshot.get("as_of")
    items = [
        _item("market.snapshot", "股票市场快照", source, as_of, "market", {
            "market_status": snapshot.get("market_status"), "is_live": snapshot.get("is_live"),
        }),
        _item("market.breadth", "市场广度", source, as_of, "market.advancing/declining", {
            "advancing": snapshot.get("advancing"), "declining": snapshot.get("declining"),
        }),
    ]
    items.extend(_item(f"market.index.{index.get('name')}", f"指数 {index.get('name')}", source, as_of, "market.indices", index) for index in snapshot.get("indices", [])[:4])
    if snapshot.get("movers"):
        items.append(_item("market.movers", "实时异动列表", source, as_of, "market.movers", snapshot.get("movers", [])[:12]))
    items.extend(_item(f"market.sector.{sector.get('name')}", f"板块 {sector.get('name')}", source, as_of, "market.sectors", sector) for sector in snapshot.get("sectors", [])[:8])
    limitations = []
    if source in {"cache", "sample"} or not snapshot.get("is_live"):
        limitations.append("股票行情不是实时直连快照，需核对刷新时间与来源。")
    return _bundle("market", items, limitations)


def cross_market_bundle(market: dict[str, Any], funds: dict[str, Any], linkage: dict[str, Any]) -> dict[str, Any]:
    items = market_bundle(market)["manifest"]
    fund_source, fund_as_of = funds.get("source"), funds.get("as_of")
    items.append(_item("fund.market", "基金全市场扫描", fund_source, fund_as_of, "fund_market", {
        "universe_count": funds.get("universe_count"), "category_counts": funds.get("category_counts"),
    }))
    for fund in funds.get("funds", [])[:12]:
        items.append(_item(f"fund.theme.{fund.get('theme')}.{fund.get('code')}", f"基金 {fund.get('name')}", fund_source, fund_as_of, "fund_market.funds", {
            "code": fund.get("code"), "theme": fund.get("theme"), "change": fund.get("change"), "nav_date": fund.get("nav_date"),
        }, caveat="基金排行基于已披露净值，不等同于盘中估值或实时持仓。"))
    for item in linkage.get("items", [])[:8]:
        items.append(_item(f"linkage.{item.get('theme')}", f"股基联动 {item.get('theme')}", "local-rules", linkage.get("as_of") or market.get("as_of"), "deterministic_linkage", item, caveat="主题映射不等同于基金最新披露持仓。"))
    limitations = list(market_bundle(market)["coverage"]["limitations"])
    if fund_source == "sample":
        limitations.append("基金扫描当前为演示数据，不能用于实际市场判断。")
    elif not funds.get("is_live"):
        limitations.append("基金净值为确认净值，可能与盘中市场变动不同步。")
    limitations.append("基金主题映射不是基金最新披露持仓。")
    return _bundle("cross_market", items, limitations)


def fund_bundle(context: dict[str, Any]) -> dict[str, Any]:
    fund, market = context.get("fund", {}), context.get("market", {})
    as_of = context.get("as_of")
    items = [
        _item(f"fund.quote.{fund.get('code')}", f"基金 {fund.get('name')}", fund.get("source", "eastmoney"), as_of, "fund", fund),
        _item("fund.penetration", "重仓股贡献估算", "local-calculation", as_of, "penetration", context.get("penetration", {}), caveat="基于公开季报与当前股票涨跌计算。"),
        _item("market.indices", "股票市场指数", market.get("source"), market.get("as_of"), "market.indices", market.get("indices", [])),
    ]
    for holding in context.get("holdings", [])[:10]:
        items.append(_item(f"fund.holding.{holding.get('stock_code')}", f"季报重仓 {holding.get('stock_name')}", "eastmoney-quarterly", holding.get("report_date"), "holdings", holding, caveat="公开季报持仓不代表当前实时持仓。"))
    return _bundle("fund", items, ["公开季报持仓不代表当前实时持仓。"])


def signal_bundle(context: dict[str, Any]) -> dict[str, Any]:
    signal, market = context.get("signal", {}), context.get("market_context", {})
    items = [
        _item(f"signal.{signal.get('code')}.{signal.get('rule_name')}", f"规则信号 {signal.get('name')}", signal.get("source"), signal.get("triggered_at"), "signal", signal),
        _item("signal.market_context", "当时市场环境", market.get("source"), market.get("as_of"), "market_context", market),
        _item("signal.daily_history", "本地日线历史", "local-storage", market.get("as_of"), "local_daily_history", context.get("local_daily_history", [])[-60:]),
    ]
    return _bundle("signal", items, ["规则信号描述的是已观测条件，不代表后续走势。"])


def bind_model_result(result: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Keep only references present in this run's manifest and expose coverage."""
    valid_ids = {item["id"] for item in bundle["manifest"]}
    requested = result.get("evidence_refs", [])
    requested = requested if isinstance(requested, list) else []
    refs = [str(item) for item in requested if str(item) in valid_ids][:6]
    coverage = dict(bundle["coverage"])
    coverage["referenced_count"] = len(refs)
    if not refs:
        coverage["status"] = "limited"
        coverage["limitations"] = [*coverage["limitations"], "模型未返回可验证的证据引用，结论应按研究草稿处理。"]
    result["evidence_refs"] = refs
    result["evidence_coverage"] = coverage
    return result
