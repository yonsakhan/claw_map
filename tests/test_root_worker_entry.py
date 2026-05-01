import unittest
from unittest.mock import patch

import worker
from src.crawler.worker import run_serial as src_run_serial


class TestRootWorkerEntry(unittest.TestCase):
    def test_root_run_serial_reexports_src_entry(self):
        self.assertIs(worker.run_serial, src_run_serial)

    def test_root_main_delegates_to_src_worker_main(self):
        with patch("worker._src_main") as main_mock:
            worker.main()

        main_mock.assert_called_once_with()

    def test_root_run_cli_initializes_logging_and_delegates(self):
        with (
            patch("worker.logging.basicConfig"),
            patch("worker.main") as main_mock,
        ):
            worker.run_cli()

        main_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
