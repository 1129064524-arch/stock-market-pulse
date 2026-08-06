import unittest
from unittest.mock import Mock, patch

from api.decision import build_decision_reference


class DecisionReferenceTests(unittest.TestCase):
    def test_builds_rule_cards_without_inventing_missing_metrics(self):
        context = {
            "stock_market": {
                "as_of": "2026-08-06T10:00:00+08:00",
                "source": "test",
                "sectors": [{
                    "name": "半导体",
                    "change": "+3.20%",
                    "stocks": "80 / 120",
                    "main_flow": "+12.5 亿",
                    "twenty_day_change": "--",
                    "pe": "--",
                    "pb": "--",
                }],
            },
            "deterministic_linkage": {"items": []},
        }
        settings = Mock(configured=False)
        with patch("api.decision.build_context", return_value=context), patch("api.decision.get_settings", return_value=settings):
            result = build_decision_reference()

        self.assertEqual(result["analysis_source"], "rules")
        self.assertEqual(result["cards"][0]["decision"], "重点跟踪")
        self.assertEqual(result["cards"][0]["pe"], "--")
        self.assertIn("+12.5 亿", result["cards"][0]["analysis"])

    def test_merges_model_explanation_without_replacing_market_metrics(self):
        context = {
            "stock_market": {
                "as_of": "2026-08-06T10:00:00+08:00",
                "source": "test",
                "sectors": [{"name": "通信设备", "change": "+2.10%", "stocks": "50 / 80", "main_flow": "+8.0 亿"}],
            },
            "deterministic_linkage": {"items": []},
        }
        settings = Mock(configured=True)
        model_result = {"cards": [{"theme": "通信设备", "decision": "趋势观察", "analysis": "板块涨幅与资金流向同步改善。", "risk": "持续性仍需下一次刷新确认。"}]}
        with patch("api.decision.build_context", return_value=context), patch("api.decision.get_settings", return_value=settings), patch("api.decision.analyze_allocation_reference", return_value=model_result):
            result = build_decision_reference()

        self.assertEqual(result["analysis_source"], "llm")
        self.assertEqual(result["cards"][0]["main_flow"], "+8.0 亿")
        self.assertEqual(result["cards"][0]["analysis"], model_result["cards"][0]["analysis"])


if __name__ == "__main__":
    unittest.main()
