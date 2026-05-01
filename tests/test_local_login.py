import unittest
from argparse import Namespace
from unittest.mock import AsyncMock, patch

from scripts import local_login


class TestLocalLogin(unittest.IsolatedAsyncioTestCase):
    def test_resolve_login_options_prefers_cli_cookie(self):
        args = Namespace(mode="cookie", cookie="cli-cookie", state_path=None)

        login_mode, cookie_string = local_login._resolve_login_options(args)

        self.assertEqual(login_mode, "cookie")
        self.assertEqual(cookie_string, "cli-cookie")

    def test_resolve_login_options_supports_cookie_json_in_mode_env_style(self):
        args = Namespace(mode='[{"name":"a","value":"1"}]', cookie=None, state_path=None)

        login_mode, cookie_string = local_login._resolve_login_options(args)

        self.assertEqual(login_mode, "cookie")
        self.assertEqual(cookie_string, '[{"name":"a","value":"1"}]')

    async def test_main_uses_cookie_login_when_cookie_mode_succeeds(self):
        scraper = type(
            "ScraperStub",
            (),
            {
                "login_with_cookie_and_save_state": AsyncMock(return_value=True),
                "login_and_save_state": AsyncMock(),
            },
        )()

        with (
            patch("scripts.local_login._parse_args", return_value=Namespace(mode="cookie", cookie="cookie-123", state_path="state.json")),
            patch("scripts.local_login.XiaohongshuScraper", return_value=scraper) as scraper_cls,
        ):
            await local_login.main([])

        scraper_cls.assert_called_once_with(
            headless=False,
            cookie_string="cookie-123",
            storage_state_path="state.json",
        )
        scraper.login_with_cookie_and_save_state.assert_awaited_once_with(cookie_string="cookie-123")
        scraper.login_and_save_state.assert_not_awaited()

    async def test_main_falls_back_to_manual_login_when_cookie_login_fails(self):
        scraper = type(
            "ScraperStub",
            (),
            {
                "login_with_cookie_and_save_state": AsyncMock(return_value=False),
                "login_and_save_state": AsyncMock(),
            },
        )()

        with (
            patch("scripts.local_login._parse_args", return_value=Namespace(mode="cookie", cookie="cookie-123", state_path=None)),
            patch("scripts.local_login.XiaohongshuScraper", return_value=scraper),
        ):
            await local_login.main([])

        scraper.login_with_cookie_and_save_state.assert_awaited_once_with(cookie_string="cookie-123")
        scraper.login_and_save_state.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
