import unittest

from api.collector_cache import MemoryCache
from api.collector_manager import Tier
from api.akshare_source import normalize_stock_frame
from api.sina_source import parse_index_payload


class CollectorSourceTests(unittest.TestCase):
    def test_parses_sina_index_payload(self):
        payload = (
            'var hq_str_s_sh000001="上证指数,3909.45,19.45,0.50,100,200";'
            'var hq_str_s_sz399001="深证成指,11940.00,-60.00,-0.50,100,200";'
        )
        result = parse_index_payload(payload)
        self.assertEqual([item["name"] for item in result], ["上证指数", "深证成指"])
        self.assertEqual(result[0]["value"], "3,909.45")
        self.assertEqual(result[0]["change"], "+0.50%")
        self.assertEqual(result[1]["direction"], "down")

    def test_memory_cache_tiers_are_namespaced(self):
        cache = MemoryCache()
        cache.set(Tier.INDICES.value, [{"name": "上证指数"}], 10)
        self.assertEqual(cache.get(Tier.INDICES.value)[0]["name"], "上证指数")
        self.assertIsNone(cache.get(Tier.FULL_SCAN.value))
        self.assertEqual(cache.get_fallback(Tier.INDICES.value)[0]["name"], "上证指数")

    def test_normalizes_akshare_stock_frame(self):
        class FakeFrame:
            columns = ["代码", "名称", "最新价", "涨跌幅", "成交额", "换手率", "所属行业"]

            def to_dict(self, orient):
                return [{"代码": "123", "名称": "测试股份", "最新价": 12.3, "涨跌幅": "2.5", "成交额": 1000, "换手率": 4.2, "所属行业": "软件"}]

        result = normalize_stock_frame(FakeFrame())
        self.assertEqual(result[0]["code"], "000123")
        self.assertEqual(result[0]["change_pct"], 2.5)
        self.assertEqual(result[0]["industry"], "软件")


if __name__ == "__main__":
    unittest.main()
