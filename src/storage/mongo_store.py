from pymongo import MongoClient
from src.config import settings


class MongoRawStore:
    def __init__(self):
        self.client = MongoClient(settings.mongo_url)
        self.collection = self.client[settings.mongo_db][settings.mongo_raw_collection]

    def upsert_profile_bundle(self, bundle: dict):
        profile = bundle.get("profile", {})
        profile_id = profile.get("id")
        if not profile_id:
            return
        self.collection.update_one(
            {"profile.id": profile_id},
            {"$set": bundle},
            upsert=True,
        )

    def count(self) -> int:
        return self.collection.count_documents({})
