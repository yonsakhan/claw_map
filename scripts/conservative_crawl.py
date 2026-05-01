"""保守采集脚本 — 低频、只抓 profile、headed 模式、遇到验证码等手动处理。

用法：
    source .venv/bin/activate
    python -m scripts.conservative_crawl              # 默认采集 10 个
    python -m scripts.conservative_crawl --limit 20   # 采集 20 个
    python -m scripts.conservative_crawl --urls urls.txt  # 从文件读取 URL
"""

import argparse
import asyncio
import logging
import random
import re
import time

from playwright.async_api import async_playwright

from src.crawler.mongo_worker import CrawlWorker, WorkerConfig
from src.storage.crawl_task_store import CrawlTaskStore
from src.storage.mongo_store import MongoRawStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ConservativeCrawl")


async def discover_profiles(limit: int) -> list[str]:
    """从小红书首页推荐中发现 profile URL。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            storage_state="src/storage/xhs_state.json",
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        # 滚动加载更多
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1500)

        anchors = await page.locator('a[href*="/user/profile/"]').all()
        seen = set()
        pids = []
        # 跳过自己的账号
        self_id = "6958829b000000001903644e"
        for a in anchors:
            href = await a.get_attribute("href") or ""
            m = re.search(r"/user/profile/([a-f0-9]+)", href)
            if m and m.group(1) not in seen and m.group(1) != self_id:
                seen.add(m.group(1))
                pids.append(m.group(1))
            if len(pids) >= limit:
                break
        await browser.close()
        return pids


def load_urls_from_file(path: str) -> list[str]:
    """从文件读取 URL 列表（每行一个）。"""
    pids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.search(r"/user/profile/([a-f0-9]+)", line)
            if m:
                pids.append(m.group(1))
            elif re.match(r"^[a-f0-9]{24}$", line):
                pids.append(line)
    return pids


async def check_login_state() -> bool:
    """检查登录态是否有效。"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            storage_state="src/storage/xhs_state.json",
            viewport={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)
        body = await page.locator("body").inner_text()
        has_content = len([l for l in body.splitlines() if l.strip()]) > 30
        await browser.close()
        return has_content


async def run(limit: int, urls_file: str | None = None):
    # 检查登录态
    import os
    if not os.path.exists("src/storage/xhs_state.json"):
        logger.error("未找到登录状态文件，请先运行: python -m scripts.local_login")
        return
    if not await check_login_state():
        logger.error("登录态已失效，请重新登录: python -m scripts.local_login")
        return
    logger.info("登录态有效")

    # 获取 profile 列表
    if urls_file:
        pids = load_urls_from_file(urls_file)
        logger.info("从文件读取 %d 个 profile", len(pids))
    else:
        logger.info("正在从首页发现 profile...")
        pids = await discover_profiles(limit)
        logger.info("发现 %d 个 profile", len(pids))

    if not pids:
        logger.warning("没有找到可采集的 profile")
        return

    # 入队
    store = CrawlTaskStore()
    for pid in pids:
        url = f"https://www.xiaohongshu.com/user/profile/{pid}"
        store.enqueue_url(
            url=url,
            payload={"account_id": pid, "source_entry": "conservative"},
            source_entry="conservative",
            force=True,
        )
    logger.info("已入队 %d 个任务", len(pids))

    # 启动 worker — headed 模式、跳过收藏、30-60 秒间隔
    worker = CrawlWorker(
        config=WorkerConfig(
            worker_id="conservative",
            max_tasks=len(pids),
            headless=False,  # headed 模式，遇到验证码可手动扫码
            min_sleep_seconds=30.0,
            max_sleep_seconds=60.0,
            max_consecutive_failures=3,
            skip_collections=True,  # 只抓 profile，不抓收藏
        ),
        task_store=store,
    )

    logger.info("开始采集（headed 模式，每个 profile 间隔 30-60 秒）")
    logger.info("遇到验证码时请用小红书 APP 扫码")
    processed = await worker.run(stop_when_idle=True)

    # 输出结果
    print("\n" + "=" * 50)
    print(f"采集完成！处理了 {processed} 个 profile")
    print(f"任务状态: {store.counts_by_status()}")

    raw_store = MongoRawStore()
    success = 0
    for pid in pids:
        raw = raw_store.get_by_account_id(pid) or {}
        profile = (raw.get("raw_data") or {}).get("profile") or {}
        stats = profile.get("stats") or {}
        status = raw.get("collection_status", "none")
        name = profile.get("display_name", "?")
        fans = stats.get("fans_count", 0)
        if status == "success":
            success += 1
        print(f"  [{status}] {name:15s} fans={fans:6d}  {pid}")

    print(f"\n成功率: {success}/{len(pids)} ({100*success/max(1,len(pids)):.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="保守采集小红书 profile")
    parser.add_argument("--limit", type=int, default=10, help="采集数量（默认 10）")
    parser.add_argument("--urls", type=str, default=None, help="从文件读取 URL（每行一个）")
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, urls_file=args.urls))


if __name__ == "__main__":
    main()
