import argparse
import asyncio
import logging
import multiprocessing as mp
import os
from typing import List

from src.crawler.scheduler import CrawlScheduler, SeedConfig
from src.crawler.worker import CrawlWorker, WorkerConfig
from src.storage.crawl_task_store import CrawlTaskStore


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--seed-explore", type=int, default=0)
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--search-limit", type=int, default=0)
    parser.add_argument("--max-tasks-per-worker", type=int, default=0)
    parser.add_argument("--lease-seconds", type=int, default=180)
    return parser.parse_args()


def _run_worker(worker_id: str, args: argparse.Namespace):
    if args.max_tasks_per_worker and args.max_tasks_per_worker > 0:
        max_tasks = int(args.max_tasks_per_worker)
    else:
        max_tasks = None
    config = WorkerConfig(
        worker_id=worker_id,
        lease_seconds=int(args.lease_seconds),
        max_tasks=max_tasks,
        headless=bool(args.headless),
    )
    worker = CrawlWorker(config=config, task_store=CrawlTaskStore())
    asyncio.run(worker.run())


async def _seed_tasks(args: argparse.Namespace):
    keywords: List[str] = [str(k) for k in (args.keyword or []) if str(k).strip()]
    search_limit = int(args.search_limit) if args.search_limit else 0
    config = SeedConfig(
        explore_limit=int(args.seed_explore),
        search_keywords=keywords if keywords else None,
        search_limit_per_keyword=search_limit if search_limit > 0 else 0,
    )
    scheduler = CrawlScheduler(task_store=CrawlTaskStore(), headless=bool(args.headless))
    await scheduler.seed(config)


def main():
    args = _parse_args()
    if args.seed_explore > 0 or (args.keyword and args.search_limit):
        asyncio.run(_seed_tasks(args))

    workers = int(args.workers)
    if workers <= 0:
        return
    ctx = mp.get_context("spawn")
    processes: List[mp.Process] = []
    for idx in range(workers):
        worker_id = f"worker_{idx+1}"
        env_var = f"PROXY_LIST_{worker_id.upper()}"
        if os.getenv(env_var):
            os.environ["PROXY_LIST"] = os.getenv(env_var) or ""
        proc = ctx.Process(target=_run_worker, args=(worker_id, args), daemon=False)
        proc.start()
        processes.append(proc)
    for proc in processes:
        proc.join()


if __name__ == "__main__":
    main()

