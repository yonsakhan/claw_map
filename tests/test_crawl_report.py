import unittest
from unittest.mock import patch

from src.analysis.crawl_report import build_report


class FakeTaskStore:
    def __init__(self):
        self.collection = object()

    def counts_by_status(self):
        return {"success": 1}


class TestCrawlReport(unittest.TestCase):
    def test_build_report_collects_errors_instead_of_failing(self):
        with (
            patch("src.analysis.crawl_report.CrawlTaskStore", return_value=FakeTaskStore()),
            patch("src.analysis.crawl_report._load_raw_store", side_effect=RuntimeError("mongo down")),
        ):
            report = build_report(sample_size=5)

        self.assertEqual(report["task_status_counts"], {"success": 1})
        self.assertEqual(report["raw_documents_total"], 0)
        self.assertEqual(report["sample_records"], [])
        self.assertTrue(any("raw_report_failed" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
