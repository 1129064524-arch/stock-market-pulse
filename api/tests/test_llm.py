import unittest
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

from api.llm import _parse_analysis_payload, reset_settings, update_settings
from api.research_evidence import bind_model_result, market_bundle
from api.main import RuleSignal, SignalAnalysisRequest, signal_analysis


class LLMProtocolTests(unittest.TestCase):
    def test_evidence_references_are_bounded_to_manifest(self):
        bundle = market_bundle({
            "as_of": "2026-08-07T10:00:00+08:00", "source": "sina", "is_live": True,
            "indices": [], "sectors": [], "advancing": 1, "declining": 0,
        })
        result = bind_model_result({"evidence_refs": ["market.breadth", "outside"]}, bundle)
        self.assertEqual(result["evidence_refs"], ["market.breadth"])
        self.assertEqual(result["evidence_coverage"]["referenced_count"], 1)

    def test_parses_chat_completion_json(self):
        payload = {"choices": [{"message": {"content": '{"stance":"中性"}'}}]}
        self.assertEqual(_parse_analysis_payload(payload, "chat_completions"), {"stance": "中性"})

    def test_parses_shared_responses_channel_json(self):
        payload = {"output": [{"content": [{"type": "output_text", "text": '```json\n{"stance":"谨慎"}\n```'}]}]}
        self.assertEqual(_parse_analysis_payload(payload, "responses"), {"stance": "谨慎"})

    def test_signal_endpoint_passes_only_normalized_local_context_to_model(self):
        signal = RuleSignal(
            code="300001", name="测试标的", rule_name="volume_breakout", rule_label="量价突破", rule_version="v1",
            score=88, evidence="涨幅与换手率同时放大", risk="波动较高", triggered_at=datetime.fromisoformat("2026-08-06T10:00:00+08:00"),
            source="test", price="10.00", change="+6.20%", sector="通信设备", direction="up", volume="3.0x",
        )
        overview = Mock()
        overview.model_dump.return_value = {"as_of": "2026-08-06T10:00:00+08:00", "market_status": "trading", "indices": [], "sectors": []}
        result_payload = {
            "summary": "规则捕捉到量价同步放大的研究线索。", "why_now": ["涨幅与换手率同时放大"],
            "confirmations": ["后续量能保持活跃"], "invalidations": ["量能快速回落"],
            "next_session_checklist": ["观察开盘后量价配合"], "risks": ["波动较高"],
            "disclaimer": "该分析仅供研究参考，不构成投资建议。",
        }
        with patch("api.main.market_overview", return_value=overview), patch("api.main.recent_daily_bars", return_value=[{"close": 10.0}]), patch("api.main.analyze_signal", return_value=result_payload) as analyze:
            result = signal_analysis(SignalAnalysisRequest(signal=signal))

        self.assertEqual(result.summary, result_payload["summary"])
        context = analyze.call_args.args[0]
        self.assertEqual(context["signal"]["code"], "300001")
        self.assertEqual(context["local_daily_history"], [{"close": 10.0}])
        self.assertNotIn("news", context)

    def test_settings_roundtrip_masks_key_and_can_reset(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"MARKET_PULSE_CONFIG_PATH": f"{directory}/.env"},
            clear=True,
        ):
            saved = update_settings({
                "base_url": "https://example.invalid/v1",
                "model": "demo-model",
                "api_key": "secret-test-key",
                "protocol": "chat_completions",
                "auto_analysis_enabled": True,
                "auto_analysis_minutes": 4,
            })
            self.assertTrue(saved["configured"])
            self.assertEqual(saved["api_key_masked"], "secr••••-key")
            self.assertNotIn("secret-test-key", str(saved))
            reset = reset_settings()
            self.assertFalse(reset["configured"])


if __name__ == "__main__":
    unittest.main()
