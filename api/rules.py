"""Small, deterministic market rules used by the signal pool.

Rules deliberately produce evidence and risk text alongside a score. They are
research prompts, not trading instructions.
"""

from __future__ import annotations

from statistics import fmean
from typing import Iterable


RULE_CATALOG = [
    {
        "name": "volume_breakout",
        "label": "量价突破",
        "version": "v1",
        "description": "涨幅与换手率同时明显抬升。",
    },
    {
        "name": "sector_resonance",
        "label": "板块共振",
        "version": "v1",
        "description": "个股走强，并得到所属行业广度的确认。",
    },
    {
        "name": "daily_trend",
        "label": "日线趋势向上",
        "version": "v1",
        "description": "收盘价、5 日均线和 20 日均线保持多头排列。",
    },
    {
        "name": "risk_breakdown",
        "label": "下行风险",
        "version": "v1",
        "description": "显著下跌或日线空头排列，提示继续观察承接。",
    },
]

RULE_LABELS = {rule["name"]: rule["label"] for rule in RULE_CATALOG}
RULE_VERSIONS = {rule["name"]: rule["version"] for rule in RULE_CATALOG}


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _price(value: object) -> str:
    return f"{_number(value):,.2f}"


def _change(value: object) -> str:
    return f"{_number(value):+.2f}%"


def _signal(
    bar: dict,
    rule_name: str,
    score: float,
    evidence: str,
    risk: str,
    direction: str,
) -> dict:
    return {
        "code": str(bar["code"]),
        "name": str(bar.get("name") or bar["code"]),
        "rule_name": rule_name,
        "rule_label": RULE_LABELS[rule_name],
        "rule_version": RULE_VERSIONS[rule_name],
        "score": max(0, min(100, round(score))),
        "evidence": evidence,
        "risk": risk,
        "triggered_at": str(bar["captured_at"]),
        "source": str(bar.get("source") or "unknown"),
        "price": _price(bar.get("price")),
        "change": _change(bar.get("change_pct")),
        "sector": str(bar.get("industry") or "全市场"),
        "direction": direction,
        "volume": f"{_number(bar.get('turnover')):.1f}% 换手",
    }


def _sector_context(bars: Iterable[dict]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for bar in bars:
        industry = str(bar.get("industry") or "其他")
        if industry in {"其他", "全市场"}:
            continue
        grouped.setdefault(industry, []).append(_number(bar.get("change_pct")))
    return {
        industry: {
            "average_change": fmean(changes),
            "up_ratio": sum(change > 0 for change in changes) / len(changes),
            "count": len(changes),
        }
        for industry, changes in grouped.items()
        if changes
    }


def _daily_trend(bars: list[dict]) -> tuple[float, float, float] | None:
    if len(bars) < 20:
        return None
    closes = [_number(bar.get("close")) for bar in bars]
    last_close = closes[-1]
    ma5 = fmean(closes[-5:])
    ma20 = fmean(closes[-20:])
    return last_close, ma5, ma20


def evaluate_rules(
    bars: list[dict], daily_histories: dict[str, list[dict]] | None = None
) -> list[dict]:
    """Evaluate versioned rules against one persisted all-market snapshot."""
    daily_histories = daily_histories or {}
    sector_context = _sector_context(bars)
    signals: list[dict] = []

    for bar in bars:
        change = _number(bar.get("change_pct"))
        turnover = _number(bar.get("turnover"))
        industry = str(bar.get("industry") or "全市场")

        if change >= 4.5 and turnover >= 4:
            score = 64 + min(change * 2.5, 20) + min(turnover * 1.25, 12)
            signals.append(
                _signal(
                    bar,
                    "volume_breakout",
                    score,
                    f"涨幅 {change:+.2f}%，换手率 {turnover:.1f}% 同步抬升。",
                    "短线乖离可能扩大，需继续观察成交承接。",
                    "up",
                )
            )

        sector = sector_context.get(industry)
        if sector and change >= 3 and sector["count"] >= 3 and sector["average_change"] >= 1 and sector["up_ratio"] >= 0.6:
            score = 60 + min(change * 2.2, 18) + min(sector["average_change"] * 4, 12) + sector["up_ratio"] * 8
            signals.append(
                _signal(
                    bar,
                    "sector_resonance",
                    score,
                    f"{industry}平均涨幅 {sector['average_change']:+.2f}%，{sector['up_ratio']:.0%} 个股上涨；该股 {change:+.2f}%。",
                    "板块联动需要持续确认，避免只凭单次冲高判断。",
                    "up",
                )
            )

        trend = _daily_trend(daily_histories.get(str(bar["code"]), []))
        if trend is not None and trend[0] > trend[1] > trend[2]:
            close, ma5, ma20 = trend
            separation = ((close / ma20) - 1) * 100 if ma20 else 0
            signals.append(
                _signal(
                    bar,
                    "daily_trend",
                    70 + min(max(separation, 0) * 2, 20),
                    f"日线收盘 {close:.2f} > MA5 {ma5:.2f} > MA20 {ma20:.2f}。",
                    "日线趋势不等于盘中持续走强，仍需结合量能验证。",
                    "up",
                )
            )
        elif change <= -4 or (trend is not None and trend[0] < trend[1] < trend[2]):
            reasons = []
            if change <= -4:
                reasons.append(f"盘中涨跌幅 {change:+.2f}%")
            if trend is not None and trend[0] < trend[1] < trend[2]:
                close, ma5, ma20 = trend
                reasons.append(f"日线收盘 {close:.2f} < MA5 {ma5:.2f} < MA20 {ma20:.2f}")
            signals.append(
                _signal(
                    bar,
                    "risk_breakdown",
                    68 + min(abs(min(change, 0)) * 3, 18) + (10 if trend is not None and trend[0] < trend[1] < trend[2] else 0),
                    "；".join(reasons) + "。",
                    "下行信号不能单独推断后续走势，关注是否止跌及量能收敛。",
                    "down",
                )
            )
    return sorted(signals, key=lambda signal: (-signal["score"], signal["code"], signal["rule_name"]))


def select_active_signals(signals: list[dict], limit: int = 160) -> list[dict]:
    """Keep the scan queue broad when a single strong sector dominates a session."""
    safe_limit = min(max(limit, 1), 300)
    quotas = {
        "volume_breakout": round(safe_limit * 0.45),
        "sector_resonance": round(safe_limit * 0.35),
        "daily_trend": round(safe_limit * 0.10),
        "risk_breakdown": round(safe_limit * 0.10),
    }
    selected: list[dict] = []
    used: set[tuple[str, str]] = set()
    selected_by_rule = {rule_name: 0 for rule_name in quotas}
    for rule_name, quota in quotas.items():
        for signal in signals:
            identity = (signal["code"], signal["rule_name"])
            if signal["rule_name"] == rule_name and identity not in used and selected_by_rule[rule_name] < quota:
                selected.append(signal)
                used.add(identity)
                selected_by_rule[rule_name] += 1
    for signal in signals:
        identity = (signal["code"], signal["rule_name"])
        if len(selected) >= safe_limit:
            break
        if identity not in used:
            selected.append(signal)
            used.add(identity)
    return sorted(selected, key=lambda signal: (-signal["score"], signal["code"], signal["rule_name"]))
