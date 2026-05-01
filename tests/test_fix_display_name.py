import tempfile
import unittest
from pathlib import Path

from scripts import fix_display_name


class TestFixDisplayName(unittest.TestCase):
    def test_infer_display_name_from_bio_after_ip_location(self):
        record = {
            "account_id": "abc123456789",
            "profile": {"bio": "一些前缀 IP属地：广东 温柔妈妈日记"},
        }

        self.assertEqual(fix_display_name.infer_display_name(record), "温柔妈妈日记")

    def test_infer_display_name_falls_back_to_account_id(self):
        record = {
            "account_id": "abc123456789",
            "profile": {"bio": ""},
        }

        self.assertEqual(fix_display_name.infer_display_name(record), "用户_abc1234567")

    def test_fix_record_replaces_only_broken_name(self):
        record = {
            "index": 2,
            "account_id": "u_100",
            "profile": {
                "display_name": "行吟信息科技（上海）有限公司",
                "bio": "IP属地：上海 城市观察者",
            },
        }

        fixed_record, changed = fix_display_name.fix_record(record)

        self.assertTrue(changed)
        self.assertEqual(fixed_record["profile"]["display_name"], "城市观察者")
        self.assertEqual(record["profile"]["display_name"], "行吟信息科技（上海）有限公司")

    def test_resolve_input_path_uses_latest_matching_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            older = reports_dir / "keyword_scout_母婴室_20260101.jsonl"
            newer = reports_dir / "keyword_scout_母婴室_20260102.jsonl"
            older.write_text("", encoding="utf-8")
            newer.write_text("", encoding="utf-8")

            resolved = fix_display_name.resolve_input_path([], reports_dir=str(reports_dir))

            self.assertEqual(resolved, newer)

    def test_process_file_writes_fixed_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "sample.jsonl"
            input_path.write_text(
                "\n".join(
                    [
                        '{"index":1,"account_id":"u_1","profile":{"display_name":"行吟信息科技（上海）有限公司","bio":"IP属地：北京 通勤育儿实验室"}}',
                        '{"index":2,"account_id":"u_2","profile":{"display_name":"正常昵称","bio":"普通简介"}}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            output_path, total_count, fixed_count = fix_display_name.process_file(input_path)
            output_text = output_path.read_text(encoding="utf-8")

            self.assertEqual(total_count, 2)
            self.assertEqual(fixed_count, 1)
            self.assertIn("通勤育儿实验室", output_text)
            self.assertIn("正常昵称", output_text)


if __name__ == "__main__":
    unittest.main()
