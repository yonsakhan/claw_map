"""
worker.py — 采集执行单元（单机串行版）

当前模式：单 Worker 串行消费 Scheduler 任务队列。
后续扩展：增大 num_workers 即可切换为单机并发，
         有代理 IP 后在 Worker.__init__ 注入 ProxyManager 即可。
"""

import asyncio
import logging
from typing import Optional

from src.crawler.scheduler import Scheduler
from src.crawler.xiaohongshu_scraper import XiaohongshuScraper
from src.crawler.proxy_manager import ProxyManager
from src.storage.mongo_store import MongoRawStore

logger = logging.getLogger("Worker")


# ──────────────────────────────────────────────
# 单个 Worker
# ──────────────────────────────────────────────

class Worker:
    def __init__(
        self,
        worker_id: str,
        scheduler: Scheduler,
        proxy_manager: Optional[ProxyManager] = None,
        headless: bool = True,
        throttle: float = 3.0,
    ):
        self.worker_id     = worker_id
        self.scheduler     = scheduler
        self.proxy_manager = proxy_manager
        self.raw_store     = MongoRawStore()
        self.headless      = headless
        self.throttle      = throttle   # 每次采集后等待秒数（反爬）

    async def run(self, max_tasks: Optional[int] = None):
        """
        串行消费任务队列直到队列为空或达到 max_tasks 上限。
        """
        done = 0
        logger.info(f"[{self.worker_id}] started")

        while True:
            if max_tasks is not None and done >= max_tasks:
                logger.info(f"[{self.worker_id}] reached max_tasks={max_tasks}, stopping")
                break

            # 从调度器领取任务
            task = await self.scheduler.acquire_task(self.worker_id)
            if task is None:
                logger.info(f"[{self.worker_id}] queue empty, exiting")
                break

            logger.info(f"[{self.worker_id}] [{done+1}] → {task.url}")

            success = await self._process_task(task)

            if success:
                self.scheduler.mark_success(task.id)
                logger.info(f"[{self.worker_id}] ✓ task {task.id}")
            else:
                self.scheduler.mark_failed(task.id)
                logger.warning(f"[{self.worker_id}] ✗ task {task.id} (will retry if quota remains)")

            done += 1
            # 随机抖动：throttle ± 0.5s，降低被反爬识别概率
            import random
            await asyncio.sleep(self.throttle + random.uniform(-0.5, 0.5))

        logger.info(f"[{self.worker_id}] finished, total processed: {done}")
        return done

    async def _process_task(self, task) -> bool:
        """
        执行单条任务的完整采集流程。
        返回 True 表示成功写入 MongoDB，False 表示需要重试。
        """
        # 1. 获取代理（暂无代理时跳过）
        proxy = None
        if self.proxy_manager and self.proxy_manager.count() > 0:
            proxy = await self.proxy_manager.get_next_proxy()
            logger.debug(f"[{self.worker_id}] using proxy: {proxy}")

        # 2. 初始化爬虫（每次任务新建，保证 Cookie/State 隔离）
        scraper = XiaohongshuScraper(headless=self.headless)

        try:
            payload = await scraper.fetch_account_dimensions(task.url)
        except Exception as e:
            logger.error(f"[{self.worker_id}] fetch error: {e}")
            return False

        if not payload:
            logger.warning(f"[{self.worker_id}] empty payload for {task.url}")
            return False

        # 3. 写入 MongoDB 原始层
        try:
            account_id = self.raw_store.upsert_profile_bundle(
                bundle=payload,
                collection_status="success",
                source=self.worker_id,
            )
            if not account_id:
                logger.error(f"[{self.worker_id}] mongo write failed (missing account_id)")
                return False
        except Exception as e:
            logger.error(f"[{self.worker_id}] mongo error: {e}")
            return False

        logger.info(f"[{self.worker_id}] saved account_id={account_id}")
        return True


# ──────────────────────────────────────────────
# 入口：单机串行运行
# ──────────────────────────────────────────────

async def run_serial(
    urls: list,
    max_tasks: Optional[int] = None,
    throttle: float = 3.0,
    headless: bool = True,
):
    """
    单机串行采集入口。

    用法示例：
        urls = ["https://www.xiaohongshu.com/user/profile/xxx", ...]
        asyncio.run(run_serial(urls, max_tasks=50))
    """
    scheduler = Scheduler()

    # 启动前清理上次未完成的 running 状态
    scheduler.reset_running()

    # 写入新 URL（已存在的自动跳过）
    added = scheduler.seed_urls(urls)
    print(f"Seeded {added} new URLs. Current stats: {scheduler.stats()}")

    worker = Worker(
        worker_id="worker_0",
        scheduler=scheduler,
        throttle=throttle,
        headless=headless,
    )

    total = await worker.run(max_tasks=max_tasks)

    stats = scheduler.stats()
    print(f"\n{'='*40}")
    print(f"Crawl finished. Processed this run: {total}")
    print(f"Task queue stats: {stats}")
    print(f"{'='*40}")
    return stats


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  # 直接传 URL")
        print("  python -m src.crawler.worker https://www.xiaohongshu.com/user/profile/xxx")
        print()
        print("  # 从文件读取（每行一个 URL）")
        print("  python -m src.crawler.worker --file urls.txt")
        sys.exit(1)

    if sys.argv[1] == "--file":
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            input_urls = [l.strip() for l in f if l.strip()]
    else:
        input_urls = sys.argv[1:]

    asyncio.run(run_serial(input_urls))
