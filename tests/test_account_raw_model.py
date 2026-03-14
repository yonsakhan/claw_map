import unittest

from src.models.account_raw import CollectionErrorCode, CollectionStatus, build_account_raw_document


class TestAccountRawModel(unittest.TestCase):
    def test_build_success_document(self):
        bundle = {
            "profile": {"id": "user_100", "bio": "test"},
            "posts": [{"id": "p1"}],
            "likes": [{"id": "l1"}],
            "favorites": [],
            "follows": [{"id": "u2"}],
        }
        document = build_account_raw_document(bundle, collection_status=CollectionStatus.SUCCESS.value)
        self.assertEqual(document["account_id"], "user_100")
        self.assertEqual(document["collection_status"], CollectionStatus.SUCCESS.value)
        self.assertEqual(document["failure"]["error_code"], CollectionErrorCode.NONE.value)
        self.assertEqual(document["stats"]["posts_count"], 1)
        self.assertEqual(document["stats"]["likes_count"], 1)
        self.assertEqual(document["stats"]["follows_count"], 1)
        self.assertIn("profile", document["raw_data"])

    def test_build_failed_document_sets_retry_marker(self):
        bundle = {
            "profile": {"id": "user_101"},
            "posts": [],
        }
        document = build_account_raw_document(
            bundle,
            collection_status=CollectionStatus.FAILED.value,
            error_code=CollectionErrorCode.RATE_LIMITED.value,
            error_message="too many requests",
        )
        self.assertEqual(document["collection_status"], CollectionStatus.FAILED.value)
        self.assertEqual(document["failure"]["error_code"], CollectionErrorCode.RATE_LIMITED.value)
        self.assertTrue(document["retry"]["retryable"])
        self.assertEqual(document["retry"]["retry_count"], 0)
        self.assertEqual(document["stats"]["posts_count"], 0)

    def test_build_document_requires_account_id(self):
        with self.assertRaises(ValueError):
            build_account_raw_document({"profile": {}, "posts": []})


if __name__ == "__main__":
    unittest.main()
