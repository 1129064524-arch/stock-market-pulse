import unittest

from api.main import app, v1_health
from api.models import MarketSnapshot, SignalEvent, StockSummary


class VersionedApiContractTests(unittest.TestCase):
    def test_core_v1_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertTrue({"/api/market/providers", "/api/research/context"}.issubset(paths))
        self.assertTrue({
            "/api/v1/system/health",
            "/api/v1/watchlist/{asset_type}",
            "/api/v1/watchlist/{asset_type}/{code}",
            "/api/v1/market/snapshot",
            "/api/v1/market/stocks",
            "/api/v1/market/stocks/{code}",
            "/api/v1/market/stocks/{code}/bars",
            "/api/v1/market/sectors",
            "/api/v1/market/movers",
            "/api/v1/funds/{code}/holdings",
            "/api/v1/linkage/fund/{code}/stocks",
            "/api/v1/analysis/funds/{code}",
            "/api/v1/analysis/funds/{code}/latest",
            "/api/v1/signals/latest",
            "/api/v1/signals/history",
            "/api/v1/signals/stats",
        }.issubset(paths))

    def test_health_and_models_validate(self):
        self.assertEqual(v1_health(), {"status": "ok"})
        MarketSnapshot(captured_at="now", indices={"上证指数": 1.0}, up_count=1, down_count=0)
        StockSummary(code="000001", name="测试", price=1, change_pct=0)
        SignalEvent(
            code="000001", name="测试", rule_name="demo", rule_version="v1", score=60,
            direction="bullish", evidence={}, risk_note="", triggered_at="now",
        )


if __name__ == "__main__":
    unittest.main()
