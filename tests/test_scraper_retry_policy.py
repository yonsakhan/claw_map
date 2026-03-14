import unittest

from src.crawler.xiaohongshu_scraper import XiaohongshuScraper


class TestScraperRetryPolicy(unittest.TestCase):
    def test_normalize_url(self):
        scraper = XiaohongshuScraper(max_fetch_retries=2)
        url = " `https://www.xiaohongshu.com/explore` "
        normalized = scraper._normalize_url(url)
        self.assertEqual(normalized, "https://www.xiaohongshu.com/explore")

    def test_should_retry_when_blocked_or_error(self):
        scraper = XiaohongshuScraper(max_fetch_retries=2)
        self.assertTrue(scraper._should_retry_fetch(0, blocked=True, has_error=False))
        self.assertTrue(scraper._should_retry_fetch(1, blocked=False, has_error=True))
        self.assertFalse(scraper._should_retry_fetch(2, blocked=True, has_error=False))
        self.assertFalse(scraper._should_retry_fetch(2, blocked=False, has_error=True))
        self.assertFalse(scraper._should_retry_fetch(1, blocked=False, has_error=False))

    def test_cookie_string_normalization_and_parse(self):
        scraper = XiaohongshuScraper(cookie_string=" `a=1; b=2` ")
        self.assertTrue(scraper._has_cookie_string())
        cookies = scraper._build_playwright_cookies(scraper.cookie_string)
        self.assertEqual(len(cookies), 2)
        self.assertEqual(cookies[0]["name"], "a")
        self.assertEqual(cookies[0]["value"], "1")
        self.assertEqual(cookies[1]["name"], "b")
        self.assertEqual(cookies[1]["value"], "2")

    def test_cookie_parse_skips_invalid_pairs(self):
        scraper = XiaohongshuScraper(cookie_string="a=1; invalid; =x; c=3")
        cookies = scraper._build_playwright_cookies(scraper.cookie_string)
        self.assertEqual([item["name"] for item in cookies], ["a", "c"])

    def test_cookie_json_array_parse(self):
        payload = '[{"domain":".xiaohongshu.com","name":"a1","value":"v1","path":"/","httpOnly":false,"secure":false},{"domain":"www.xiaohongshu.com","name":"acw_tc","value":"v2","expirationDate":1800000000}]'
        scraper = XiaohongshuScraper(cookie_string=payload)
        cookies = scraper._build_playwright_cookies(scraper.cookie_string)
        self.assertEqual(len(cookies), 2)
        self.assertEqual(cookies[0]["name"], "a1")
        self.assertEqual(cookies[0]["domain"], ".xiaohongshu.com")
        self.assertEqual(cookies[1]["name"], "acw_tc")
        self.assertIn("expires", cookies[1])

    def test_parse_profile_text(self):
        raw_text = """
        一枚亚高配
        小红书号：1575353133IP属地：广东
        分享好用好玩的。
        钱并没有消失，而是变成了喜欢的样子。
        🫰点个关注呗
        处女座
        广东广州
        vlog博主
        2关注
        1347粉丝
        5639获赞与收藏
        关注
        笔记
        收藏
        """
        scraper = XiaohongshuScraper()
        parsed = scraper._parse_profile_text(raw_text)
        self.assertEqual(parsed["display_name"], "一枚亚高配")
        self.assertEqual(parsed["account_no"], "1575353133")
        self.assertEqual(parsed["ip_location"], "广东")
        self.assertEqual(parsed["follow_count"], 2)
        self.assertEqual(parsed["fans_count"], 1347)
        self.assertEqual(parsed["likes_favorites_count"], 5639)
        self.assertIn("笔记", parsed["tabs"])


if __name__ == "__main__":
    unittest.main()
