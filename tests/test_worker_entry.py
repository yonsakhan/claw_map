import unittest
from unittest.mock import patch

from src.crawler.worker import run_serial


class FakeCollection:
    def __init__(self):
        self.rows = []

    def find(self, query, projection):
        del projection
        task_ids = set(query.get("task_id", {}).get("$in", []))
        return [{"status": row["status"]} for row in self.rows if row["task_id"] in task_ids]


class FakeTaskStore:
    def __init__(self):
        self.collection = FakeCollection()
        self.enqueued_urls = []

    def enqueue_url(self, url, payload=None, source_entry=None, **kwargs):
        del kwargs
        task_id = f"task-{len(self.enqueued_urls) + 1}"
        self.enqueued_urls.append(
            {
                "url": url,
                "payload": payload or {},
                "source_entry": source_entry,
                "task_id": task_id,
            }
        )
        self.collection.rows.append({"task_id": task_id, "status": "success"})
        return {"task_id": task_id, "inserted": True, "status": "pending"}


class FakeCrawlWorker:
    created = []

    def __init__(self, config, task_store):
        self.config = config
        self.task_store = task_store
        FakeCrawlWorker.created.append(self)

    async def run(self, stop_when_idle=False):
        self.stop_when_idle = stop_when_idle
        return 2


class TestWorkerEntry(unittest.IsolatedAsyncioTestCase):
    async def test_run_serial_delegates_to_crawl_worker(self):
        FakeCrawlWorker.created.clear()
        task_store = FakeTaskStore()

        with (
            patch("src.crawler.worker.CrawlTaskStore", return_value=task_store),
            patch("src.crawler.worker.CrawlWorker", FakeCrawlWorker),
        ):
            stats, processed = await run_serial(
                urls=["https://a.example/u1", "https://a.example/u2"],
                max_tasks=5,
                throttle=2.5,
                headless=False,
            )

        self.assertEqual(processed, 2)
        self.assertEqual(stats, {"success": 2})
        self.assertEqual([item["url"] for item in task_store.enqueued_urls], ["https://a.example/u1", "https://a.example/u2"])
        self.assertEqual(task_store.enqueued_urls[0]["source_entry"], "legacy_worker")
        self.assertEqual(len(FakeCrawlWorker.created), 1)
        worker = FakeCrawlWorker.created[0]
        self.assertEqual(worker.config.worker_id, "worker_0")
        self.assertEqual(worker.config.max_tasks, 2)
        self.assertFalse(worker.config.headless)
        self.assertEqual(worker.config.collector_throttle_seconds, 2.5)
        self.assertTrue(worker.stop_when_idle)

    async def test_run_serial_returns_empty_result_for_blank_urls(self):
        task_store = FakeTaskStore()
        FakeCrawlWorker.created.clear()

        with (
            patch("src.crawler.worker.CrawlTaskStore", return_value=task_store),
            patch("src.crawler.worker.CrawlWorker", FakeCrawlWorker),
        ):
            stats, processed = await run_serial(urls=["", "  "], max_tasks=None, throttle=3.0, headless=True)

        self.assertEqual(stats, {})
        self.assertEqual(processed, 0)
        self.assertEqual(len(FakeCrawlWorker.created), 0)


if __name__ == "__main__":
    unittest.main()
