import argparse
import asyncio
import logging
from typing import Dict, Optional

from src.crawler.mongo_worker import CrawlWorker, WorkerConfig
from src.storage.crawl_task_store import CrawlTaskStore


logger = logging.getLogger("Worker")

async def run_serial(
    urls: list[str],
    max_tasks: Optional[int] = None,
    throttle: float = 3.0,
    headless: bool = True,
):
    logger.warning("src.crawler.worker is a legacy entrypoint; delegating execution to CrawlWorker.")
    task_store = CrawlTaskStore()
    task_ids: list[str] = []
    for url in urls:
        normalized_url = str(url or "").strip()
        if not normalized_url:
            continue
        enqueue_result = task_store.enqueue_url(
            url=normalized_url,
            payload={"source_entry": "legacy_worker"},
            source_entry="legacy_worker",
        )
        task_id = str(enqueue_result.get("task_id", "")).strip()
        if task_id and task_id not in task_ids:
            task_ids.append(task_id)

    if not task_ids:
        return {}, 0

    target_tasks = len(task_ids)
    if max_tasks is not None:
        target_tasks = min(target_tasks, int(max_tasks))

    config = WorkerConfig(
        worker_id="worker_0",
        min_sleep_seconds=max(0.0, float(throttle) * 0.8),
        max_sleep_seconds=max(0.0, float(throttle) * 1.2),
        collector_throttle_seconds=max(0.0, float(throttle)),
        max_tasks=target_tasks,
        headless=bool(headless),
    )
    worker = CrawlWorker(config=config, task_store=task_store)
    processed = await worker.run(stop_when_idle=True)
    return _legacy_stats(task_store, task_ids), processed


def _legacy_stats(task_store: CrawlTaskStore, task_ids: list[str]) -> Dict[str, int]:
    rows = task_store.collection.find({"task_id": {"$in": list(task_ids)}}, {"status": 1, "_id": 0})
    stats: Dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "")
        if not status:
            continue
        stats[status] = stats.get(status, 0) + 1
    return stats


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
