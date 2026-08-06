import unittest

from api.funds import parse_directory_payload, parse_rank_payload


class FundProtocolTests(unittest.TestCase):
    def test_parses_fund_directory(self):
        payload = 'var r = [["000001","HXCZHH","华夏成长混合","混合型-灵活","PINYIN"]];'
        self.assertEqual(parse_directory_payload(payload), {"000001": "混合型-灵活"})

    def test_parses_fund_market_ranking(self):
        payload = 'var rankData = {datas:["000001,华夏成长混合,HXCZHH,2026-08-05,1.2345,2.3456,3.21,1.20,4.50,8.00,12.00,20.00,30.00,40.00,10.00,50.00,2001-01-01"],allRecords:20072,pageIndex:1,pageNum:1,allPages:20072,allNum:20072,zs_count:4457,gp_count:1082,hh_count:8472,zq_count:4844,qdii_count:223,fof_count:993};'
        funds, total, counts = parse_rank_payload(payload, {"000001": "混合型-灵活"})
        self.assertEqual(total, 20072)
        self.assertEqual(funds[0]["change"], "+3.21%")
        self.assertEqual(funds[0]["signal"], "趋势改善")
        self.assertEqual(counts["混合型"], 8472)


if __name__ == "__main__":
    unittest.main()
