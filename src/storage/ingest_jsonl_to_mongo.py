import json
import os
import sys

sys.path.append(os.getcwd())
from src.storage.mongo_store import MongoRawStore


def ingest(file_path: str):
    store = MongoRawStore()
    inserted = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                bundle = json.loads(line)
            except json.JSONDecodeError:
                continue
            store.upsert_profile_bundle(bundle)
            inserted += 1
    print(f"Ingested/Updated: {inserted}")
    print(f"Mongo Collection Count: {store.count()}")


if __name__ == "__main__":
    ingest("dummy_data.jsonl")
