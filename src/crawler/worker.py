import argparse
import asyncio
import logging
import random
from typing import Optional

from src.crawler.scheduler import Scheduler
from src.crawler.xiaohongshu_scraper import XiaohongshuScraper
from src.storage.mongo_store import MongoRawStore


logger = logging.getLogger("Worker")


class Worker:
    def __init__(
        self,
        worker_id: str,
        scheduler: Scheduler,
        headless: bool = True,
        throttle: float = 3.0,
    ):
        self.worker_id = worker_id
        self.scheduler = scheduler
        self.raw_store = MongoRawStore()
        self.headless = headless
        self.throttle = throttle

    async def run(self, max_tasks: Optional[int] = None) -> int:
        done = 0
        while True:
            if max_tasks is not None and done >= max_tasks:
                break
            task = await self.scheduler.acquire_task(self.worker_id)
            if task is None:
                break
            ok, err = await self._process_task(task.url)
            if ok:
                self.scheduler.mark_success(task.id)
            else:
                self.scheduler.mark_failed(task.id, error=err)
            done += 1
            await asyncio.sleep(self.throttle + random.uniform(-0.5, 0.5))
        return done

    async def _process_task(self, url: str) -> tuple[bool, str]:
        scraper = XiaohongshuScraper(headless=self.headless)
        try:
            payload = await scraper.fetch_account_dimensions(url)
            if not payload:
                return False, "empty payload"
            collections = await scraper.fetch_collections(url)
            payload["collections"] = collections
            account_id = self.raw_store.upsert_profile_bundle(
                bundle=payload,
                collection_status="success",
                source=self.worker_id,
            )
            if not account_id:
                return False, "mongo upsert failed"
            return True, ""
        except Exception as exc:
            return False, str(exc)


async def run_serial(
    urls: list[str],
    max_tasks: Optional[int] = None,
    throttle: float = 3.0,
    headless: bool = True,
):
    scheduler = Scheduler()
    scheduler.reset_running()
    scheduler.seed_urls(urls)
    worker = Worker(worker_id="worker_0", scheduler=scheduler, throttle=throttle, headless=headless)
    processed = await worker.run(max_tasks=max_tasks)
    return scheduler.stats(), processed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*", default=[])
    parser.add_argument("--file", dest="file", default=None)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--throttle", type=float, default=3.0)
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


def main():
    args = _parse_args()
    urls: list[str] = []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            urls.extend([line.strip() for line in f if line.strip()])
    urls.extend([u for u in (args.urls or []) if str(u).strip()])
    max_tasks = int(args.max_tasks) if args.max_tasks and int(args.max_tasks) > 0 else None
    stats, processed = asyncio.run(
        run_serial(
            urls=urls,
            max_tasks=max_tasks,
            throttle=float(args.throttle),
            headless=bool(args.headless),
        )
    )
    print(f"processed={processed}")
    print(f"stats={stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
