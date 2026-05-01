import unittest
from unittest.mock import patch

import main


class TestRootMainEntry(unittest.TestCase):
    def test_root_main_delegates_to_run_large_scale_crawl(self):
        with patch("main.run_large_scale_crawl.main") as main_mock:
            main.main()

        main_mock.assert_called_once_with()

    def test_root_run_cli_initializes_logging_and_delegates(self):
        with (
            patch("main.logging.basicConfig"),
            patch("main.main") as main_mock,
        ):
            main.run_cli()

        main_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
