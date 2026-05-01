import argparse
import asyncio
import logging
import multiprocessing as mp
import os
from typing import List

from src.config import AgentRuntimeConfig, apply_agent_runtime_config, load_agent_runtime_config
from src.crawler.mongo_scheduler import CrawlScheduler, SeedConfig
from src.crawler.mongo_worker import CrawlWorker, WorkerConfig
from src.storage.crawl_task_store import CrawlTaskStore


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--headless", dest="headless", action="store_true")
    parser.add_argument("--headed", dest="headless", action="store_false")
    parser.set_defaults(headless=None)
    parser.add_argument("--seed-explore", type=int, default=None)
    parser.add_argument("--keyword", action="append", default=None)
    parser.add_argument("--search-limit", type=int, default=None)
    parser.add_argument("--max-tasks-per-worker", type=int, default=None)
    parser.add_argument("--lease-seconds", type=int, default=None)
    parser.add_argument("--idle-timeout", type=float, default=None,
                        help="Worker exits after this many seconds with no tasks (0 = never)")
    return parser.parse_args()


def _resolve_runtime_options(args: argparse.Namespace) -> tuple[AgentRuntimeConfig, dict]:
    runtime_config = load_agent_runtime_config(args.config)
    apply_agent_runtime_config(runtime_config)

    workers = int(args.workers) if args.workers is not None else int(runtime_config.num_workers)
    if str(runtime_config.mode).lower() == "serial" and args.workers is None:
        workers = 1

    headless = bool(args.headless) if args.headless is not None else bool(runtime_config.headless)
    throttle_seconds = max(0.0, float(runtime_config.throttle_seconds))
    sleep_min = max(0.0, throttle_seconds * 0.8)
    sleep_max = max(sleep_min, throttle_seconds * 1.2)
    max_tasks = args.max_tasks_per_worker if args.max_tasks_per_worker is not None else runtime_config.max_tasks_per_run
    lease_seconds = int(args.lease_seconds) if args.lease_seconds is not None else 180
    seed_explore = int(args.seed_explore) if args.seed_explore is not None else int(runtime_config.seed_explore_limit)
    keywords = [str(k) for k in (args.keyword or runtime_config.seed_search_keywords or []) if str(k).strip()]
    search_limit = int(args.search_limit) if args.search_limit is not None else int(runtime_config.seed_search_limit_per_keyword)
    idle_timeout = float(args.idle_timeout) if args.idle_timeout is not None else 300.0

    return runtime_config, {
        "workers": workers,
        "headless": headless,
        "throttle_seconds": throttle_seconds,
        "sleep_min": sleep_min,
        "sleep_max": sleep_max,
        "max_tasks": int(max_tasks) if max_tasks is not None else 0,
        "lease_seconds": lease_seconds,
        "seed_explore": seed_explore,
        "keywords": keywords,
        "search_limit": search_limit,
        "idle_timeout": idle_timeout,
    }


def _run_worker(worker_id: str, runtime_options: dict):
    if runtime_options["max_tasks"] and runtime_options["max_tasks"] > 0:
        max_tasks = int(runtime_options["max_tasks"])
    else:
        max_tasks = None
    config = WorkerConfig(
        worker_id=worker_id,
        lease_seconds=int(runtime_options["lease_seconds"]),
        min_sleep_seconds=float(runtime_options["sleep_min"]),
        max_sleep_seconds=float(runtime_options["sleep_max"]),
        collector_throttle_seconds=float(runtime_options["throttle_seconds"]),
        max_tasks=max_tasks,
        headless=bool(runtime_options["headless"]),
        idle_timeout=float(runtime_options.get("idle_timeout", 0)),
    )
    worker = CrawlWorker(config=config, task_store=CrawlTaskStore())
    asyncio.run(worker.run())


async def _seed_tasks(runtime_options: dict):
    keywords: List[str] = [str(k) for k in (runtime_options["keywords"] or []) if str(k).strip()]
    search_limit = int(runtime_options["search_limit"]) if runtime_options["search_limit"] else 0
    config = SeedConfig(
        explore_limit=int(runtime_options["seed_explore"]),
        search_keywords=keywords if keywords else None,
        search_limit_per_keyword=search_limit if search_limit > 0 else 0,
    )
    scheduler = CrawlScheduler(task_store=CrawlTaskStore(), headless=bool(runtime_options["headless"]))
    await scheduler.seed(config)


def main():
    args = _parse_args()
    runtime_config, runtime_options = _resolve_runtime_options(args)
    if runtime_options["seed_explore"] > 0 or (runtime_options["keywords"] and runtime_options["search_limit"]):
        asyncio.run(_seed_tasks(runtime_options))

    workers = int(runtime_options["workers"])
    if workers <= 0:
        return
    ctx = mp.get_context("spawn")
    processes: List[mp.Process] = []
    for idx in range(workers):
        worker_id = f"worker_{idx+1}"
        env_var = f"{runtime_config.proxy_env_prefix}{idx+1}" if runtime_config.proxy_enabled else f"PROXY_LIST_{worker_id.upper()}"
        if os.getenv(env_var):
            os.environ["PROXY_LIST"] = os.getenv(env_var) or ""
        proc = ctx.Process(target=_run_worker, args=(worker_id, runtime_options), daemon=False)
        proc.start()
        processes.append(proc)
    for proc in processes:
        proc.join()


if __name__ == "__main__":
    main()
