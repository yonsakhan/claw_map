import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

import src.config as config_module
from src.config import apply_agent_runtime_config, load_agent_runtime_config


class TestConfig(unittest.TestCase):
    def test_invalid_numeric_env_values_fall_back_to_defaults(self):
        with patch.dict(
            os.environ,
            {
                "XHS_MIN_DELAY_SECONDS": "bad",
                "XHS_MAX_DELAY_SECONDS": "oops",
                "XHS_RATE_LIMIT_COOLDOWN_SECONDS": "nope",
            },
            clear=False,
        ):
            reloaded = importlib.reload(config_module)
            self.assertEqual(reloaded.settings.xhs_min_delay_seconds, 8.0)
            self.assertEqual(reloaded.settings.xhs_max_delay_seconds, 15.0)
            self.assertEqual(reloaded.settings.xhs_rate_limit_cooldown_seconds, 1800)

        importlib.reload(config_module)

    def test_load_agent_runtime_config_resolves_yaml_and_env_placeholders(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as fp:
            fp.write(
                "\n".join(
                    [
                        "mode: parallel",
                        "num_workers: 3",
                        "headless: false",
                        "throttle_seconds: 2.5",
                        "max_tasks_per_run: 7",
                        "postgres_url: ${POSTGRES_URL}",
                        "mongo_url: ${MONGO_URL}",
                        "proxy:",
                        "  enabled: true",
                        "  per_worker_env_prefix: PROXY_LIST_WORKER_",
                        "seed:",
                        "  explore_limit: 11",
                        "  search_keywords: [alpha, beta]",
                        "  search_limit_per_keyword: 22",
                    ]
                )
            )
            config_path = fp.name

        with patch.dict(
            os.environ,
            {"POSTGRES_URL": "postgresql://demo", "MONGO_URL": "mongodb://demo"},
            clear=False,
        ):
            runtime = load_agent_runtime_config(config_path)

        self.assertEqual(runtime.mode, "parallel")
        self.assertEqual(runtime.num_workers, 3)
        self.assertFalse(runtime.headless)
        self.assertEqual(runtime.throttle_seconds, 2.5)
        self.assertEqual(runtime.max_tasks_per_run, 7)
        self.assertEqual(runtime.postgres_url, "postgresql://demo")
        self.assertEqual(runtime.mongo_url, "mongodb://demo")
        self.assertTrue(runtime.proxy_enabled)
        self.assertEqual(runtime.proxy_env_prefix, "PROXY_LIST_WORKER_")
        self.assertEqual(runtime.seed_explore_limit, 11)
        self.assertEqual(runtime.seed_search_keywords, ["alpha", "beta"])
        self.assertEqual(runtime.seed_search_limit_per_keyword, 22)

    def test_apply_agent_runtime_config_updates_runtime_settings(self):
        runtime = load_agent_runtime_config(None)
        runtime.postgres_url = "postgresql://override"
        runtime.mongo_url = "mongodb://override"

        original_postgres_url = config_module.settings.postgres_url
        original_mongo_url = config_module.settings.mongo_url
        try:
            apply_agent_runtime_config(runtime)
            self.assertEqual(config_module.settings.postgres_url, "postgresql://override")
            self.assertEqual(config_module.settings.mongo_url, "mongodb://override")
        finally:
            config_module.settings.postgres_url = original_postgres_url
            config_module.settings.mongo_url = original_mongo_url


if __name__ == "__main__":
    unittest.main()
