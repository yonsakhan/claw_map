from pymongo import MongoClient
from src.config import settings
from src.models.account_raw import build_account_raw_document


class MongoRawStore:
    def __init__(self):
        self.client = MongoClient(settings.mongo_url)
        self.collection = self.client[settings.mongo_db][settings.mongo_raw_collection]
        self.collection.create_index("account_id", unique=True)
        self.collection.create_index("collection_status")
        self.collection.create_index("retry.retryable")

    def upsert_profile_bundle(
        self,
        bundle: dict,
        collection_status: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retryable: bool | None = None,
        retry_count: int | None = None,
        max_retries: int = 3,
        source: str | None = None,
    ) -> str | None:
        try:
            document = build_account_raw_document(
                bundle=bundle,
                collection_status=collection_status,
                error_code=error_code,
                error_message=error_message,
                retryable=retryable,
                retry_count=retry_count,
                max_retries=max_retries,
                source=source,
            )
        except ValueError:
            return None

        account_id = document["account_id"]
        self.collection.update_one(
            {"account_id": account_id},
            {"$set": document},
            upsert=True,
        )
        return account_id

    def count(self) -> int:
        return self.collection.count_documents({})

    def get_by_account_id(self, account_id: str) -> dict | None:
        if not account_id:
            return None
        return self.collection.find_one({"account_id": str(account_id)})
