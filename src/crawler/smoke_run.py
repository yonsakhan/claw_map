import asyncio
import json
import os

from src.crawler.worker import CrawlWorker, WorkerConfig
from src.storage.crawl_task_store import CrawlTaskStore
from src.storage.mongo_store import MongoRawStore


async def main():
    os.makedirs("reports", exist_ok=True)
    url = "https://www.xiaohongshu.com/user/profile/5b15392b4260905102559902"
    task_store = CrawlTaskStore()
    task_store.enqueue_url(
        url=url,
        payload={"account_id": "5b15392b4260905102559902", "source_entry": "manual_smoke"},
        source_entry="manual_smoke",
        priority=10,
    )

    raw_store = MongoRawStore()
    worker = CrawlWorker(
        config=WorkerConfig(worker_id="smoke_worker", max_tasks=1, headless=True),
        task_store=task_store,
        raw_store=raw_store,
    )
    await worker.run()

    task = task_store.collection.find_one({"url": url}) or {}
    raw = raw_store.get_by_account_id("5b15392b4260905102559902") or {}
    out = {
        "task_status": task.get("status"),
        "task_error": task.get("last_error"),
        "raw_status": raw.get("collection_status"),
        "raw_error": (raw.get("failure") or {}).get("error_message"),
        "profile_keys": sorted(list(((raw.get("raw_data") or {}).get("profile") or {}).keys())),
        "collections_items_count": (raw.get("stats") or {}).get("collections_items_count"),
    }
    with open("reports/smoke_run.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(main())

