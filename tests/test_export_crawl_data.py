import csv
import tempfile
import unittest
from unittest.mock import patch

from src.storage.export_crawl_data import export_csv


class TestExportCrawlData(unittest.TestCase):
    def test_export_csv_streams_rows_without_buffering_all_documents(self):
        documents = [
            {
                "source": "manual",
                "raw_data": {
                    "profile": {
                        "display_name": "A",
                        "xhs_id": "x1",
                        "profile_url": "https://example.com/u1",
                    },
                    "collections": {"folders": [], "items": [{"id": "n1"}]},
                },
            },
            {
                "source": "manual",
                "raw_data": {
                    "profile": {
                        "display_name": "B",
                        "xhs_id": "x2",
                        "profile_url": "https://example.com/u2",
                    },
                    "collections": {"folders": [], "items": []},
                },
            },
        ]

        with tempfile.NamedTemporaryFile("r+", encoding="utf-8-sig", newline="", suffix=".csv") as tmp:
            with patch("src.storage.export_crawl_data._iter_raw_documents", return_value=iter(documents)):
                export_csv(tmp.name)

            tmp.seek(0)
            rows = list(csv.DictReader(tmp))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["display_name"], "A")
        self.assertEqual(rows[0]["items_count"], "1")
        self.assertEqual(rows[1]["display_name"], "B")


if __name__ == "__main__":
    unittest.main()
