from collections import defaultdict

from api.collector import _number


THEME_SECTOR_KEYWORDS = {
    "半导体": ("半导体", "电子", "元件", "光学光电子"),
    "科技成长": ("通信", "计算机", "软件", "互联网", "半导体", "电子"),
    "消费": ("食品", "饮料", "白酒", "家电", "零售", "美容"),
    "医药医疗": ("医药", "医疗", "生物", "制药"),
    "新能源": ("电力设备", "光伏", "电池", "汽车"),
    "国防军工": ("军工", "航空", "航天", "船舶"),
    "宽基 / 指数": (),
}


def _percent(value: object) -> float:
    return _number(str(value or "0").replace("%", ""))


def _state(fund_change: float, sector_change: float) -> str:
    if fund_change >= 0.5 and sector_change >= 0.5:
        return "共振向上"
    if fund_change <= -0.5 and sector_change <= -0.5:
        return "共振向下"
    if fund_change * sector_change < 0:
        return "出现背离"
    return "同步观察"


def build_cross_market_overview(market: dict, fund_market: dict) -> dict:
    funds_by_theme: dict[str, list[dict]] = defaultdict(list)
    for fund in fund_market.get("funds", []):
        funds_by_theme[str(fund.get("theme") or "未分类")].append(fund)

    sectors = market.get("sectors", [])
    items = []
    for theme, funds in funds_by_theme.items():
        keywords = THEME_SECTOR_KEYWORDS.get(theme, (theme,))
        matched_sectors = [sector for sector in sectors if not keywords or any(keyword in sector.get("name", "") for keyword in keywords)]
        fund_change = sum(_percent(fund.get("change")) for fund in funds) / max(len(funds), 1)
        sector_change = sum(_percent(sector.get("change")) for sector in matched_sectors) / max(len(matched_sectors), 1) if matched_sectors else 0.0
        state = _state(fund_change, sector_change)
        confidence = min(95, 55 + min(len(funds) * 4, 20) + (15 if matched_sectors else 0) + (5 if "共振" in state else 0))
        items.append({
            "theme": theme,
            "fund_count": len(funds),
            "fund_change": f"{fund_change:+.2f}%",
            "sector_change": f"{sector_change:+.2f}%" if matched_sectors else "--",
            "sectors": [sector.get("name", "") for sector in matched_sectors[:3]],
            "state": state,
            "confidence": confidence,
            "note": f"基金侧 {len(funds)} 只样本；股票侧匹配 {len(matched_sectors)} 个板块",
            "basis": "基金名称/类型与股票板块的风格映射，不等同于基金披露持仓",
        })
    items.sort(key=lambda item: ("共振" not in item["state"], -item["confidence"], item["theme"]))
    return {
        "as_of": market.get("as_of") or fund_market.get("as_of"),
        "stock_source": market.get("source", "sample"),
        "fund_source": fund_market.get("source", "sample"),
        "stock_signal_count": len(market.get("movers", [])),
        "fund_signal_count": len(fund_market.get("funds", [])),
        "items": items[:12],
    }
