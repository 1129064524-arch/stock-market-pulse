import unittest

from api.linkage import build_cross_market_overview


class CrossMarketLinkageTests(unittest.TestCase):
    def test_detects_stock_fund_resonance(self):
        market = {"as_of": "2026-08-06T10:00:00+08:00", "source": "sample", "movers": [{"code": "1"}], "sectors": [{"name": "半导体", "change": "+3.00%"}]}
        funds = {"source": "sample", "funds": [{"theme": "半导体", "change": "+2.00%"}, {"theme": "半导体", "change": "+1.00%"}]}
        result = build_cross_market_overview(market, funds)
        self.assertEqual(result["items"][0]["state"], "共振向上")
        self.assertEqual(result["items"][0]["sector_change"], "+3.00%")
        self.assertIn("不等同于基金披露持仓", result["items"][0]["basis"])


if __name__ == "__main__":
    unittest.main()
