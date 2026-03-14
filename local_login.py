import asyncio
import os
from src.crawler.xiaohongshu_scraper import XiaohongshuScraper

async def main():
    raw_mode = (os.getenv("XHS_LOGIN_MODE") or "manual").strip()
    cookie_env = (os.getenv("XHS_COOKIE") or "").strip()
    inferred_cookie = raw_mode if raw_mode.startswith("[") else ""
    scraper = XiaohongshuScraper(headless=False, cookie_string=cookie_env or inferred_cookie)
    login_mode = "cookie" if inferred_cookie else raw_mode.lower()
    if login_mode == "cookie":
        ok = await scraper.login_with_cookie_and_save_state()
        if ok:
            return
        print("Cookie 登录失败，切换到手动登录...")
    await scraper.login_and_save_state()

if __name__ == "__main__":
    asyncio.run(main())
