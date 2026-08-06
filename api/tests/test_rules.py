import os
import tempfile
import unittest
from datetime import datetime

from api.rules import evaluate_rules, select_active_signals
from api.storage import initialize, record_rule_events, recent_signal_events


def bar(code: str, name: str, change: float, turnover: float, industry: str = "通信设备") -> dict:
    return {
        "captured_at": "2026-08-06T10:00:00+08:00",
        "code": code,
        "name": name,
        "price": 10.0,
        "change_pct": change,
        "amount": 1_000_000_000,
        "turnover": turnover,
        "industry": industry,
        "source": "test",
    }


class RuleEvaluationTests(unittest.TestCase):
    def test_outputs_explainable_positive_and_risk_signals(self):
        bars = [
            bar("300001", "甲", 6.2, 7.0),
            bar("300002", "乙", 2.4, 3.0),
            bar("300003", "丙", 1.8, 2.0),
            bar("300004", "丁", -5.1, 4.0, "汽车整车"),
        ]
        history = [{"close": 8 + index * 0.1} for index in range(20)]
        signals = evaluate_rules(bars, {"300001": history})
        signal_types = {(item["code"], item["rule_name"]) for item in signals}
        self.assertIn(("300001", "volume_breakout"), signal_types)
        self.assertIn(("300001", "sector_resonance"), signal_types)
        self.assertIn(("300001", "daily_trend"), signal_types)
        self.assertIn(("300004", "risk_breakdown"), signal_types)
        self.assertTrue(all(item["evidence"] and item["risk"] and item["rule_version"] == "v1" for item in signals))

    def test_active_queue_balances_rule_types_and_respects_limit(self):
        signals = [
            {"code": f"{index:06d}", "rule_name": "sector_resonance", "score": 99 - index}
            for index in range(20)
        ] + [
            {"code": f"{100 + index:06d}", "rule_name": "volume_breakout", "score": 98 - index}
            for index in range(20)
        ] + [{"code": "000999", "rule_name": "risk_breakdown", "score": 80}]
        active = select_active_signals(signals, limit=10)
        self.assertEqual(len(active), 10)
        self.assertGreaterEqual(sum(item["rule_name"] == "volume_breakout" for item in active), 4)
        self.assertGreaterEqual(sum(item["rule_name"] == "sector_resonance" for item in active), 3)
        self.assertIn("risk_breakdown", {item["rule_name"] for item in active})


class RuleStorageTests(unittest.TestCase):
    def test_rule_events_respect_cooldown_and_keep_version(self):
        old_path = os.environ.get("MARKET_DB_PATH")
        with tempfile.TemporaryDirectory() as directory:
            os.environ["MARKET_DB_PATH"] = f"{directory}/rules.sqlite3"
            initialize()
            signal = {
                "triggered_at": datetime.fromisoformat("2026-08-06T10:00:00+08:00").isoformat(),
                "code": "300001", "name": "甲", "rule_name": "volume_breakout", "rule_version": "v1",
                "score": 88, "evidence": "测试证据", "risk": "测试风险", "source": "test",
            }
            self.assertEqual(record_rule_events([signal]), 1)
            self.assertEqual(record_rule_events([signal]), 0)
            events = recent_signal_events()
            self.assertEqual(events[0]["rule_version"], "v1")
        if old_path is None:
            os.environ.pop("MARKET_DB_PATH", None)
        else:
            os.environ["MARKET_DB_PATH"] = old_path


if __name__ == "__main__":
    unittest.main()
