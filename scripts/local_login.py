import argparse
import asyncio
import os

from src.crawler.xiaohongshu_scraper import XiaohongshuScraper


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="刷新并保存小红书登录态")
    parser.add_argument("--mode", choices=["manual", "cookie"], default=None)
    parser.add_argument("--cookie", default=None, help="直接传入 Cookie 字符串或 JSON 数组")
    parser.add_argument("--state-path", default=None, help="登录态文件输出路径")
    return parser.parse_args(argv)


def _resolve_login_options(args: argparse.Namespace) -> tuple[str, str]:
    raw_mode = str(args.mode or os.getenv("XHS_LOGIN_MODE") or "manual").strip()
    inferred_cookie = raw_mode if raw_mode.startswith("[") else ""
    if args.cookie is not None:
        cookie_value = str(args.cookie).strip()
    elif inferred_cookie:
        cookie_value = inferred_cookie
    else:
        cookie_value = str(os.getenv("XHS_COOKIE") or "").strip()
    cookie_string = cookie_value
    login_mode = "cookie" if inferred_cookie else raw_mode.lower()
    if cookie_string and login_mode != "manual":
        login_mode = "cookie"
    return login_mode, cookie_string


async def main(argv: list[str] | None = None):
    args = _parse_args(argv)
    login_mode, cookie_string = _resolve_login_options(args)
    scraper_kwargs = {"headless": False, "cookie_string": cookie_string}
    if args.state_path:
        scraper_kwargs["storage_state_path"] = str(args.state_path)
    scraper = XiaohongshuScraper(**scraper_kwargs)
    if login_mode == "cookie":
        ok = await scraper.login_with_cookie_and_save_state(cookie_string=cookie_string)
        if ok:
            return
        print("Cookie 登录失败，切换到手动登录...")
    await scraper.login_and_save_state()


if __name__ == "__main__":
    asyncio.run(main())
