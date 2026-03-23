import json
import random
from collections import Counter
from typing import Any, Dict, List, Optional

from pymongo import MongoClient

from src.config import settings
from src.crawler.user_record import build_user_record, calculate_missing_rate
from src.storage.crawl_task_store import CrawlTaskStore


def _load_raw_store():
    client = MongoClient(settings.mongo_url)
    return client[settings.mongo_db][settings.mongo_raw_collection]


def build_report(sample_size: int = 100) -> Dict[str, Any]:
    task_store = CrawlTaskStore()
    status_counts = task_store.counts_by_status()

    raw_collection = _load_raw_store()
    total_raw = raw_collection.count_documents({})

    tasks_collection = task_store.collection
    finished = list(tasks_collection.find({"status": {"$in": ["success", "dead", "retry", "failed"]}}, {"started_at": 1, "finished_at": 1, "status": 1}))
    durations = []
    for task in finished:
        started_at = task.get("started_at")
        finished_at = task.get("finished_at")
        if started_at and finished_at:
            durations.append((finished_at - started_at).total_seconds())
    avg_seconds_per_user = round(sum(durations) / len(durations), 2) if durations else None
    users_per_hour = round(3600 / avg_seconds_per_user, 2) if avg_seconds_per_user and avg_seconds_per_user > 0 else None

    missing_rates: List[float] = []
    missing_key_counter: Counter = Counter()
    sample_records: List[Dict[str, Any]] = []

    if total_raw > 0:
        sample_n = min(int(sample_size), int(total_raw))
        sample_skip = max(int(total_raw) - sample_n, 0)
        docs = list(raw_collection.find({}, limit=sample_n, skip=random.randint(0, sample_skip)))
        for doc in docs:
            raw_data = doc.get("raw_data", {}) or {}
            profile = raw_data.get("profile", {}) or {}
            collections = raw_data.get("collections", {}) or {"folders": [], "items": []}
            record = build_user_record(profile=profile, collections=collections, source_entry=str(doc.get("source") or ""))
            rate, missing_keys = calculate_missing_rate(record)
            missing_rates.append(rate)
            missing_key_counter.update(missing_keys)
            record["missing_rate"] = rate
            record["missing_keys"] = missing_keys
            record["account_id"] = doc.get("account_id")
            sample_records.append(record)

    avg_missing = round(sum(missing_rates) / len(missing_rates), 4) if missing_rates else None
    return {
        "task_status_counts": status_counts,
        "raw_documents_total": total_raw,
        "avg_seconds_per_user": avg_seconds_per_user,
        "estimated_users_per_hour": users_per_hour,
        "sample_size": len(sample_records),
        "sample_avg_missing_rate": avg_missing,
        "sample_missing_key_top": missing_key_counter.most_common(20),
        "sample_records": sample_records,
    }


def write_report(path: str = "reports/crawl_report.json", sample_size: int = 100):
    report = build_report(sample_size=sample_size)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    write_report()
