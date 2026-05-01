import json
import tempfile
import unittest
from unittest.mock import patch

from src.analysis.dashboard import AnalysisDashboard


class TestAnalysisDashboard(unittest.TestCase):
    def test_dashboard_records_postgres_failure_and_falls_back_to_jsonl(self):
        rows = [
            {
                "original_id": "u1",
                "age_group": "25-29",
                "income_level": "Medium",
                "fertility_status": "Trying",
            }
        ]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as fp:
            for row in rows:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            data_file = fp.name

        with patch("src.analysis.dashboard.get_engine", side_effect=RuntimeError("postgres down")):
            dashboard = AnalysisDashboard(data_file=data_file, use_postgres=True)

        self.assertEqual(dashboard.data_source, "jsonl")
        self.assertIn("postgres load failed", dashboard.load_error or "")
        self.assertEqual(len(dashboard.df), 1)


if __name__ == "__main__":
    unittest.main()
