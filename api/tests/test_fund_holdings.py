import unittest

from api.fund_holdings import calculate_holdings_pct, parse_holdings_payload


class FundHoldingTests(unittest.TestCase):
    def test_parses_public_holdings_table(self):
        html = """
        <table><tr><th>股票代码</th><th>股票名称</th><th>占净值比</th></tr>
        <tr><td>688981</td><td>中芯国际</td><td>8.50%</td></tr>
        <tr><td>300308</td><td>中际旭创</td><td>6.20%</td></tr></table>
        """
        holdings = parse_holdings_payload(html, "2026-06-30")
        self.assertEqual(holdings[0]["stock_code"], "688981")
        self.assertEqual(holdings[0]["weight_pct"], 8.5)
        self.assertEqual(holdings[0]["report_date"], "2026-06-30")

    def test_calculates_weighted_contribution_and_skips_missing_quotes(self):
        holdings = [
            {"stock_code": "688981", "stock_name": "中芯国际", "weight_pct": 8.5, "report_date": "2026-06-30"},
            {"stock_code": "300308", "stock_name": "中际旭创", "weight_pct": 6.2, "report_date": "2026-06-30"},
        ]
        result = calculate_holdings_pct(holdings, {"688981": 2.0})
        self.assertAlmostEqual(result["penetration_pct"], 0.17)
        self.assertEqual(len(result["contributors"]), 1)

    def test_decodes_eastmoney_javascript_wrapper(self):
        payload = r'''var apidata={content:"<table><tr><td>000001</td><td>平安银行</td><td>4.25%</td></tr></table>"};'''
        holdings = parse_holdings_payload(payload, "2026-03-31")
        self.assertEqual(holdings[0]["stock_name"], "平安银行")
        self.assertEqual(holdings[0]["weight_pct"], 4.25)


if __name__ == "__main__":
    unittest.main()
