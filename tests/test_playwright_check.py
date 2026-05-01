import asyncio
import os

import pytest
from playwright.async_api import async_playwright


async def _run_playwright_smoke():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.baidu.com", wait_until="domcontentloaded")
        title = await page.title()
        await browser.close()
        return title


def test_playwright():
    """Playwright 冒烟测试（默认跳过）。

    说明：该测试依赖系统浏览器运行时依赖 + 外网访问。
    在 CI/离线环境下容易失败，因此默认跳过；需要时设置 RUN_PLAYWRIGHT_SMOKE=1。
    """

    if os.getenv("RUN_PLAYWRIGHT_SMOKE") != "1":
        pytest.skip("set RUN_PLAYWRIGHT_SMOKE=1 to enable playwright smoke test")

    try:
        title = asyncio.run(_run_playwright_smoke())
    except Exception as exc:
        pytest.fail(f"playwright smoke failed: {exc}")
    assert title
