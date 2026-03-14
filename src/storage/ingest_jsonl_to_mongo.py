import json
import os
import sys

sys.path.append(os.getcwd())
from src.storage.mongo_store import MongoRawStore


def ingest(file_path: str):
    store = MongoRawStore()
    inserted = 0
    skipped = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                bundle = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            account_id = store.upsert_profile_bundle(bundle, source=file_path)
            if account_id:
                inserted += 1
            else:
                skipped += 1
    print(f"Ingested/Updated: {inserted}")
    print(f"Skipped: {skipped}")
    print(f"Mongo Collection Count: {store.count()}")


if __name__ == "__main__":
    ingest("dummy_data.jsonl")
