import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Optional

from src.crawler.account_collector import AccountCollector
from src.crawler.user_record import build_user_record, calculate_missing_rate
from src.crawler.xiaohongshu_scraper import XiaohongshuScraper
from src.storage.crawl_task_store import CrawlTaskStore
from src.storage.mongo_store import MongoRawStore


logger = logging.getLogger("CrawlWorker")


@dataclass
class WorkerConfig:
    worker_id: str
    lease_seconds: int = 180
    min_sleep_seconds: float = 1.2
    max_sleep_seconds: float = 3.5
    max_tasks: Optional[int] = None
    headless: bool = True


class CrawlWorker:
    def __init__(
        self,
        config: WorkerConfig,
        task_store: Optional[CrawlTaskStore] = None,
        raw_store: Optional[MongoRawStore] = None,
    ):
        self.config = config
        self.task_store = task_store or CrawlTaskStore()
        self.raw_store = raw_store or MongoRawStore()
        self.collector = AccountCollector(raw_store=self.raw_store, throttle_seconds=0.4, max_retries=2)
        self.scraper = XiaohongshuScraper(headless=config.headless)

    async def run(self):
        processed = 0
        while True:
            if self.config.max_tasks is not None and processed >= int(self.config.max_tasks):
                break
            task = self.task_store.lease_next(self.config.worker_id, lease_seconds=self.config.lease_seconds)
            if not task:
                await asyncio.sleep(2.0)
                continue
            try:
                await self._process_task(task)
                processed += 1
                await asyncio.sleep(random.uniform(self.config.min_sleep_seconds, self.config.max_sleep_seconds))
            except Exception as exc:
                self.task_store.mark_failed(task.get("task_id", ""), error=str(exc), retryable=True)
                await asyncio.sleep(random.uniform(2.0, 4.5))
        logger.info(f"Worker {self.config.worker_id} finished, processed={processed}")

    async def _process_task(self, task: dict):
        task_id = str(task.get("task_id", ""))
        url = str(task.get("url", ""))
        payload = task.get("payload", {}) or {}
        source_entry = str(task.get("source_entry", "")) or str(payload.get("source_entry", ""))

        async def profile_loader():
            dimensions = await self.scraper.fetch_account_dimensions(url)
            if not dimensions:
                raise RuntimeError("profile fetch returned None")
            return dimensions

        async def collections_loader():
            return await self.scraper.fetch_collections(url)

        result = await self.collector.collect(
            account_id=payload.get("account_id") or url,
            profile_loader=profile_loader,
            collections_loader=collections_loader,
            source=source_entry or "crawl_worker",
        )
        account_id = result.get("account_id")
        raw_document = self.raw_store.get_by_account_id(account_id) if account_id else None
        record_profile = {}
        record_collections = {"folders": [], "items": []}
        if raw_document:
            raw_data = raw_document.get("raw_data", {}) or {}
            record_profile = raw_data.get("profile", {}) or {}
            record_collections = raw_data.get("collections", {}) or {"folders": [], "items": []}
        user_record = build_user_record(record_profile, record_collections, source_entry=source_entry or "crawl_worker")
        missing_rate, missing_keys = calculate_missing_rate(user_record)
        meta = {
            "account_id": account_id,
            "collection_status": result.get("collection_status"),
            "missing_rate": missing_rate,
            "missing_keys": missing_keys,
        }
        retryable = bool(result.get("failures"))
        if result.get("collection_status") == "failed":
            self.task_store.mark_failed(task_id, error=str(result.get("failures")), retryable=retryable)
        else:
            self.task_store.mark_success(task_id, meta=meta)

