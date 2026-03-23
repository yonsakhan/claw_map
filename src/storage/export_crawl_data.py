import csv
import json
import os
from typing import Any, Dict, Iterable, Optional

from pymongo import MongoClient

from src.config import settings
from src.crawler.user_record import build_user_record, calculate_missing_rate, flatten_for_csv


def _iter_raw_documents(limit: Optional[int] = None) -> Iterable[Dict[str, Any]]:
    client = MongoClient(settings.mongo_url)
    collection = client[settings.mongo_db][settings.mongo_raw_collection]
    cursor = collection.find({}, sort=[("_id", 1)])
    if limit is not None:
        cursor = cursor.limit(int(limit))
    for doc in cursor:
        yield doc


def export_jsonl(output_path: str, limit: Optional[int] = None):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in _iter_raw_documents(limit=limit):
            raw_data = doc.get("raw_data", {}) or {}
            profile = raw_data.get("profile", {}) or {}
            collections = raw_data.get("collections", {}) or {"folders": [], "items": []}
            record = build_user_record(profile=profile, collections=collections, source_entry=str(doc.get("source") or ""))
            missing_rate, missing_keys = calculate_missing_rate(record)
            record["missing_rate"] = missing_rate
            record["missing_keys"] = missing_keys
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def export_csv(output_path: str, limit: Optional[int] = None):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    rows = []
    for doc in _iter_raw_documents(limit=limit):
        raw_data = doc.get("raw_data", {}) or {}
        profile = raw_data.get("profile", {}) or {}
        collections = raw_data.get("collections", {}) or {"folders": [], "items": []}
        record = build_user_record(profile=profile, collections=collections, source_entry=str(doc.get("source") or ""))
        rows.append(flatten_for_csv(record))
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    export_jsonl("data/crawled_users.jsonl", limit=None)
    export_csv("data/crawled_users.csv", limit=None)
