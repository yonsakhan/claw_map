import unittest
from argparse import Namespace
from unittest.mock import patch

from src.crawler.run_large_scale_crawl import _resolve_runtime_options


class TestRunLargeScaleCrawl(unittest.TestCase):
    def test_runtime_options_merge_cli_with_yaml_config(self):
        args = Namespace(
            config="/tmp/nonexistent.yaml",
            workers=None,
            headless=None,
            seed_explore=None,
            keyword=None,
            search_limit=None,
            max_tasks_per_worker=None,
            lease_seconds=None,
        )

        class FakeRuntimeConfig:
            mode = "parallel"
            num_workers = 3
            headless = False
            throttle_seconds = 2.5
            max_tasks_per_run = 7
            postgres_url = "postgresql://demo"
            mongo_url = "mongodb://demo"
            proxy_enabled = True
            proxy_env_prefix = "PROXY_LIST_WORKER_"
            seed_explore_limit = 11
            seed_search_keywords = ["alpha", "beta"]
            seed_search_limit_per_keyword = 22

        with (
            patch("src.crawler.run_large_scale_crawl.load_agent_runtime_config", return_value=FakeRuntimeConfig()),
            patch("src.crawler.run_large_scale_crawl.apply_agent_runtime_config"),
        ):
            runtime_config, runtime_options = _resolve_runtime_options(args)

        self.assertEqual(runtime_config.num_workers, 3)
        self.assertEqual(runtime_options["workers"], 3)
        self.assertFalse(runtime_options["headless"])
        self.assertEqual(runtime_options["throttle_seconds"], 2.5)
        self.assertEqual(runtime_options["max_tasks"], 7)
        self.assertEqual(runtime_options["seed_explore"], 11)
        self.assertEqual(runtime_options["keywords"], ["alpha", "beta"])
        self.assertEqual(runtime_options["search_limit"], 22)

    def test_serial_mode_defaults_to_single_worker_when_cli_not_set(self):
        args = Namespace(
            config="/tmp/nonexistent.yaml",
            workers=None,
            headless=None,
            seed_explore=None,
            keyword=None,
            search_limit=None,
            max_tasks_per_worker=None,
            lease_seconds=None,
        )

        class FakeRuntimeConfig:
            mode = "serial"
            num_workers = 4
            headless = True
            throttle_seconds = 3.0
            max_tasks_per_run = 0
            postgres_url = None
            mongo_url = None
            proxy_enabled = False
            proxy_env_prefix = "PROXY_LIST_WORKER_"
            seed_explore_limit = 0
            seed_search_keywords = None
            seed_search_limit_per_keyword = 0

        with (
            patch("src.crawler.run_large_scale_crawl.load_agent_runtime_config", return_value=FakeRuntimeConfig()),
            patch("src.crawler.run_large_scale_crawl.apply_agent_runtime_config"),
        ):
            _, runtime_options = _resolve_runtime_options(args)

        self.assertEqual(runtime_options["workers"], 1)


if __name__ == "__main__":
    unittest.main()
