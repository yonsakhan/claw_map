import os
import unittest
import tempfile
from unittest.mock import AsyncMock, patch

from src.crawler.errors import LoginRequiredError, RateLimitedError
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

    def test_parse_profile_text_note_count(self):
        raw_text = "笔记・2\n收藏\n"
        scraper = XiaohongshuScraper()
        parsed = scraper._parse_profile_text(raw_text)
        self.assertEqual(parsed["note_count"], 2)

    def test_parse_collection_items_html(self):
        html = """
        <div class="feeds-container static-layout">
          <section class="note-item static-layout">
            <a class="cover mask ld" href="/user/profile/66e8d3d8000000001d030c44/6985b5c1000000000d009494?xsec_source=pc_collect"></a>
            <a class="title"><span>超详细‼️道医资格证～拿证全流程🔥</span></a>
            <div class="author-wrapper"><span class="name">姚姚考证咨询</span></div>
          </section>
        </div>
        """
        scraper = XiaohongshuScraper()
        items = scraper._parse_collection_items_from_html(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["note_id"], "6985b5c1000000000d009494")
        self.assertEqual(items[0]["url"], "https://www.xiaohongshu.com/explore/6985b5c1000000000d009494")
        self.assertEqual(items[0]["author"], "姚姚考证咨询")


class TestScraperLoginAndThrottle(unittest.IsolatedAsyncioTestCase):
    class _PageStub:
        def __init__(self):
            self.url = ""

        async def goto(self, url, wait_until=None, timeout=None):
            self.url = url

        async def wait_for_load_state(self, _state, _timeout=None):
            return None

    class _ContextStub:
        def __init__(self, page):
            self.page = page
            self.saved_path = None
            self.init_scripts = []
            self.cookies = []
            self.kwargs = None

        async def add_cookies(self, cookies):
            self.cookies.extend(cookies)

        async def add_init_script(self, script):
            self.init_scripts.append(script)

        async def new_page(self):
            return self.page

        async def storage_state(self, path):
            self.saved_path = path

    class _BrowserStub:
        def __init__(self, context):
            self.context = context
            self.closed = False

        async def new_context(self, **kwargs):
            self.context.kwargs = kwargs
            return self.context

        async def close(self):
            self.closed = True

    class _AsyncPlaywrightStub:
        def __init__(self, playwright):
            self.playwright = playwright

        async def __aenter__(self):
            return self.playwright

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def test_persist_storage_state_supports_bare_filename(self):
        class ContextStub:
            def __init__(self):
                self.saved_path = None

            async def storage_state(self, path):
                self.saved_path = path

        scraper = XiaohongshuScraper(storage_state_path="xhs_state.json")
        context = ContextStub()

        await scraper._persist_storage_state(context)

        self.assertEqual(context.saved_path, "xhs_state.json")

    async def test_before_navigation_uses_single_target_gap(self):
        scraper = XiaohongshuScraper()
        scraper.runtime_store = type(
            "RuntimeStoreStub",
            (),
            {"get_rate_limit_cooldown_until_epoch": lambda _self: None},
        )()
        scraper.min_delay_seconds = 8
        scraper.max_delay_seconds = 15
        scraper._last_request_at = 100.0

        sleep_mock = AsyncMock()
        with (
            patch("src.crawler.xiaohongshu_scraper.random.uniform", return_value=10.0),
            patch("src.crawler.xiaohongshu_scraper.time.monotonic", side_effect=[105.0, 115.0, 115.0]),
            patch("src.crawler.xiaohongshu_scraper.asyncio.sleep", sleep_mock),
        ):
            await scraper._before_navigation()

        sleep_mock.assert_awaited_once_with(5.0)
        self.assertEqual(scraper._last_request_at, 115.0)

    async def test_headless_ensure_logged_in_returns_false_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = f"{tmpdir}/xhs_state.json"
            scraper = XiaohongshuScraper(headless=True, storage_state_path=state_path, cookie_string="")
            self.assertFalse(await scraper.ensure_logged_in())
            self.assertFalse(os.path.exists(state_path))

    async def test_before_navigation_respects_shared_cooldown(self):
        scraper = XiaohongshuScraper()
        scraper.min_delay_seconds = 0
        scraper.max_delay_seconds = 0
        scraper.runtime_store = type(
            "RuntimeStoreStub",
            (),
            {"get_rate_limit_cooldown_until_epoch": lambda _self: 120.0},
        )()

        sleep_mock = AsyncMock()
        with (
            patch("src.crawler.xiaohongshu_scraper.random.uniform", return_value=0.0),
            patch("src.crawler.xiaohongshu_scraper.time.monotonic", side_effect=[10.0, 30.0, 31.0]),
            patch("src.crawler.xiaohongshu_scraper.time.time", return_value=100.0),
            patch("src.crawler.xiaohongshu_scraper.asyncio.sleep", sleep_mock),
        ):
            await scraper._before_navigation()

        sleep_mock.assert_awaited_once_with(20.0)

    def test_enter_rate_limit_cooldown_updates_shared_store(self):
        calls = []
        scraper = XiaohongshuScraper()
        scraper.runtime_store = type(
            "RuntimeStoreStub",
            (),
            {
                "set_rate_limit_cooldown": lambda _self, seconds, reason="", source="": calls.append(
                    {"seconds": seconds, "reason": reason, "source": source}
                )
            },
        )()

        with patch("src.crawler.xiaohongshu_scraper.os.getpid", return_value=1234):
            scraper._enter_rate_limit_cooldown("rate limited")

        self.assertEqual(calls[0]["seconds"], scraper.rate_limit_cooldown_seconds)
        self.assertEqual(calls[0]["reason"], "rate limited")
        self.assertEqual(calls[0]["source"], "pid:1234")

    async def test_run_with_scraper_session_closes_browser_on_error(self):
        scraper = XiaohongshuScraper(storage_state_path="missing_state.json", cookie_string="")
        page = self._PageStub()
        context = self._ContextStub(page)
        browser = self._BrowserStub(context)

        async def failing_action(page_obj, _context_obj, use_state):
            self.assertIs(page_obj, page)
            self.assertFalse(use_state)
            raise RuntimeError("boom")

        with (
            patch.object(scraper, "_launch_browser", AsyncMock(return_value=browser)),
            patch.object(scraper, "_get_random_user_agent", AsyncMock(return_value="test-ua")),
        ):
            with self.assertRaises(RuntimeError):
                await scraper._run_with_scraper_session(object(), failing_action, viewport={"width": 1, "height": 1})

        self.assertTrue(browser.closed)

    def test_raise_login_block_invalidates_state_and_enters_cooldown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = f"{tmpdir}/xhs_state.json"
            with open(state_path, "w", encoding="utf-8") as f:
                f.write("{}")

            scraper = XiaohongshuScraper(storage_state_path=state_path)
            with patch.object(scraper, "_enter_rate_limit_cooldown") as cooldown_mock:
                with self.assertRaises(RateLimitedError):
                    scraper._raise_login_block(
                        scene="search",
                        reason="website_login_error: 300013 too many requests",
                        use_state=True,
                    )

            self.assertFalse(os.path.exists(state_path))
            cooldown_mock.assert_called_once()

    async def test_collect_accounts_from_search_raises_when_login_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = f"{tmpdir}/xhs_state.json"
            with open(state_path, "w", encoding="utf-8") as f:
                f.write("{}")

            scraper = XiaohongshuScraper(storage_state_path=state_path, cookie_string="")
            page = self._PageStub()
            context = self._ContextStub(page)
            browser = self._BrowserStub(context)

            with (
                patch("src.crawler.xiaohongshu_scraper.async_playwright", return_value=self._AsyncPlaywrightStub(object())),
                patch.object(scraper, "_launch_browser", AsyncMock(return_value=browser)),
                patch.object(scraper, "_get_random_user_agent", AsyncMock(return_value="test-ua")),
                patch.object(scraper, "_before_navigation", AsyncMock()),
                patch.object(scraper, "_random_sleep", AsyncMock()),
                patch.object(
                    scraper,
                    "_get_login_block_reason",
                    AsyncMock(return_value=(True, "selector_visible: .login-container")),
                ),
            ):
                with self.assertRaises(LoginRequiredError):
                    await scraper.collect_accounts_from_search("https://www.xiaohongshu.com/search_result?keyword=test")

            self.assertTrue(browser.closed)
            self.assertFalse(os.path.exists(state_path))


if __name__ == "__main__":
    unittest.main()
