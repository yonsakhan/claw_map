import unittest

from src.crawler.user_record import build_user_record, calculate_missing_rate, flatten_for_csv


class TestUserRecordSchema(unittest.TestCase):
    def test_missing_rate(self):
        record = build_user_record(profile={}, collections={}, source_entry="test")
        rate, missing_keys = calculate_missing_rate(record)
        self.assertGreater(rate, 0.0)
        self.assertIn("profile.display_name", missing_keys)
        self.assertIn("collections.folders", missing_keys)

    def test_flatten_for_csv(self):
        record = build_user_record(
            profile={
                "display_name": "u",
                "xhs_id": "123",
                "bio": "b",
                "follow_count": 1,
                "fans_count": 2,
                "likes_favorites_count": 3,
                "profile_url": "https://www.xiaohongshu.com/user/profile/abc",
            },
            collections={"folders": [], "items": []},
            source_entry="explore",
        )
        row = flatten_for_csv(record)
        self.assertEqual(row["display_name"], "u")
        self.assertEqual(row["folders_count"], 0)


if __name__ == "__main__":
    unittest.main()

