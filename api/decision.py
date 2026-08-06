"""Sector decision-reference cards built from local market evidence."""

from api.llm import LLMConfigurationError, LLMProviderError, analyze_allocation_reference, get_settings
from api.orchestrator import build_context


DECISIONS = {"重点跟踪", "逢低核对", "持有观望", "风险收敛", "趋势观察"}


def _fallback_decision(change: float) -> str:
    if change >= 3:
        return "重点跟踪"
    if change <= -3:
        return "风险收敛"
    if change >= 1:
        return "趋势观察"
    return "持有观望"


def _percent(value: object) -> float:
    try:
        return float(str(value or "0").replace("%", ""))
    except (TypeError, ValueError):
        return 0.0


def _fallback_cards(sectors: list[dict]) -> list[dict]:
    cards = []
    for sector in sectors[:8]:
        change = _percent(sector.get("change"))
        decision = _fallback_decision(change)
        flow = sector.get("main_flow", "--")
        cards.append({
            "theme": sector.get("name", "未分类"),
            "day_change": sector.get("change", "--"),
            "twenty_day_change": sector.get("twenty_day_change", "--"),
            "pe": sector.get("pe", "--"),
            "pb": sector.get("pb", "--"),
            "main_flow": flow,
            "decision": decision,
            "analysis": f"今日{sector.get('change', '--')}，覆盖 {sector.get('stocks', '--')}；资金 {flow}。",
            "risk": "估值与 20 日数据待补。",
        })
    return cards


def build_decision_reference() -> dict:
    context = build_context()
    sectors = context["stock_market"].get("sectors", [])
    fallback = _fallback_cards(sectors)
    analysis_source = "rules"
    if get_settings().configured and fallback:
        try:
            model_result = analyze_allocation_reference({
                "sectors": sectors[:8],
                "deterministic_linkage": context["deterministic_linkage"],
            })
            by_theme = {item["theme"]: item for item in model_result.get("cards", []) if item.get("theme")}
            for card in fallback:
                model_card = by_theme.get(card["theme"])
                if not model_card:
                    continue
                decision = model_card.get("decision")
                if decision in DECISIONS:
                    card["decision"] = decision
                if model_card.get("analysis"):
                    card["analysis"] = str(model_card["analysis"])[:280]
                if model_card.get("risk"):
                    card["risk"] = str(model_card["risk"])[:180]
            analysis_source = "llm"
        except (LLMConfigurationError, LLMProviderError, ValueError, TypeError):
            analysis_source = "rules"
    return {
        "as_of": context["stock_market"].get("as_of"),
        "source": context["stock_market"].get("source", "sample"),
        "analysis_source": analysis_source,
        "cards": fallback,
        "disclaimer": "仅供研究参考，不构成投资建议；缺失估值和 20 日数据已明确标注。",
    }
