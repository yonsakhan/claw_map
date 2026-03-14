import unittest

from src.crawler.account_collector import AccountCollector
from src.models.account_raw import CollectionErrorCode, CollectionStatus


class FakeRawStore:
    def __init__(self):
        self.payload = None
        self.kwargs = None

    def upsert_profile_bundle(self, bundle, **kwargs):
        self.payload = bundle
        self.kwargs = kwargs
        return bundle.get("account_id")


class TestAccountCollector(unittest.IsolatedAsyncioTestCase):
    async def test_collect_multidimensional_bundle_and_partial_status(self):
        store = FakeRawStore()
        collector = AccountCollector(raw_store=store, throttle_seconds=0, max_retries=1)

        async def load_profile():
            return {
                "profile": {"id": "u_1", "bio": "新手妈妈"},
                "posts": [{"id": "p1", "title": "遛娃公园推荐"}],
            }

        async def load_likes():
            return [{"id": "l1", "title": "地铁通勤经验"}]

        async def load_favorites():
            raise RuntimeError("rate limited")

        async def load_follows():
            return [{"id": "f1", "name": "育儿号"}]

        result = await collector.collect(
            account_id="u_1",
            profile_loader=load_profile,
            likes_loader=load_likes,
            favorites_loader=load_favorites,
            follows_loader=load_follows,
            source="unit_test",
        )
        self.assertEqual(result["account_id"], "u_1")
        self.assertEqual(result["collection_status"], CollectionStatus.PARTIAL.value)
        self.assertEqual(result["failures"][0]["error_code"], CollectionErrorCode.RATE_LIMITED.value)
        self.assertEqual(store.payload["account_id"], "u_1")
        self.assertEqual(len(store.payload["collection_log"]), 4)
        self.assertEqual(store.kwargs["collection_status"], CollectionStatus.PARTIAL.value)
