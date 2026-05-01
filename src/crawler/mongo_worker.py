import asyncio
import logging
import random
import time
from contextlib import suppress
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
    collector_throttle_seconds: float = 0.4
    max_tasks: Optional[int] = None
    headless: bool = True
    idle_timeout: float = 0.0
    max_consecutive_failures: int = 5
    skip_collections: bool = False


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
        self.collector = AccountCollector(
            raw_store=self.raw_store,
            throttle_seconds=float(self.config.collector_throttle_seconds),
            max_retries=2,
        )
        self.scraper = XiaohongshuScraper(headless=config.headless)

    async def _lease_heartbeat(self, task_id: str):
        interval = max(5.0, float(self.config.lease_seconds) / 3.0)
        while True:
            await asyncio.sleep(interval)
            refreshed = self.task_store.refresh_lease(
                task_id=task_id,
                worker_id=self.config.worker_id,
                lease_seconds=self.config.lease_seconds,
            )
            if not refreshed:
                logger.warning("Task lease heartbeat lost for %s", task_id)
                return

    async def run(self, stop_when_idle: bool = False) -> int:
        processed = 0
        consecutive_failures = 0
        idle_since: Optional[float] = None
        idle_timeout = float(self.config.idle_timeout or 0)
        max_consecutive = int(self.config.max_consecutive_failures or 5)
        while True:
            if self.config.max_tasks is not None and processed >= int(self.config.max_tasks):
                break
            if consecutive_failures >= max_consecutive:
                logger.warning("Worker %s hit %d consecutive failures, stopping",
                               self.config.worker_id, consecutive_failures)
                break
            task = self.task_store.lease_next(self.config.worker_id, lease_seconds=self.config.lease_seconds)
            if not task:
                if stop_when_idle:
                    break
                if idle_timeout > 0:
                    now = time.monotonic()
                    if idle_since is None:
                        idle_since = now
                    elif now - idle_since >= idle_timeout:
                        logger.info("Worker %s idle for %.0fs, exiting", self.config.worker_id, idle_timeout)
                        break
                await asyncio.sleep(2.0)
                continue
            idle_since = None
            try:
                await self._process_task(task)
                processed += 1
                consecutive_failures = 0
                await asyncio.sleep(random.uniform(self.config.min_sleep_seconds, self.config.max_sleep_seconds))
            except Exception as exc:
                consecutive_failures += 1
                marked = self.task_store.mark_failed(
                    task.get("task_id", ""),
                    worker_id=self.config.worker_id,
                    error=str(exc),
                    retryable=True,
                )
                if not marked:
                    logger.warning("Failed to mark task %s as failed after exception", task.get("task_id", ""))
                await asyncio.sleep(random.uniform(2.0, 4.5))
        logger.info(f"Worker {self.config.worker_id} finished, processed={processed}")
        return processed

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

        collections_loader = None
        if not self.config.skip_collections:
            async def _collections_loader():
                return await self.scraper.fetch_collections(url)
            collections_loader = _collections_loader

        heartbeat = asyncio.create_task(self._lease_heartbeat(task_id))
        try:
            result = await self.collector.collect(
                account_id=payload.get("account_id") or url,
                profile_loader=profile_loader,
                collections_loader=collections_loader,
                source=source_entry or "crawl_worker",
            )
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
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
        has_failures = bool(result.get("failures"))
        retryable = bool(result.get("retryable"))
        if has_failures:
            marked = self.task_store.mark_failed(
                task_id,
                worker_id=self.config.worker_id,
                error=str(result.get("failures")),
                retryable=retryable,
            )
            if not marked:
                logger.warning("Failed to mark task %s as failed after collection", task_id)
        else:
            marked = self.task_store.mark_success(task_id, worker_id=self.config.worker_id, meta=meta)
            if not marked:
                logger.warning("Failed to mark task %s as success", task_id)
