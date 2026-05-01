from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pymongo import MongoClient, ReturnDocument

from src.config import settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CrawlTaskStore:
    def __init__(self):
        self.client = MongoClient(settings.mongo_url)
        self.collection = self.client[settings.mongo_db][settings.mongo_task_collection]
        self.collection.create_index("task_id", unique=True)
        self.collection.create_index("status")
        self.collection.create_index("url", unique=True)
        self.collection.create_index("locked_until")

    def enqueue_url(
        self,
        url: str,
        task_type: str = "user_profile",
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        source_entry: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        task_id = str(uuid4())
        document = {
            "task_id": task_id,
            "task_type": task_type,
            "url": str(url),
            "payload": payload or {},
            "priority": int(priority),
            "source_entry": source_entry or "",
            "status": "pending",
            "retry_count": 0,
            "max_retries": 3,
            "locked_by": None,
            "locked_until": None,
            "last_error": None,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        result = self.collection.update_one(
            {"url": document["url"]},
            {"$setOnInsert": document},
            upsert=True,
        )
        if force:
            self.reset_task(url)
        current = self.collection.find_one({"url": document["url"]}, {"task_id": 1, "status": 1}) or {}
        return {
            "task_id": str(current.get("task_id") or task_id),
            "inserted": bool(result.upserted_id),
            "status": str(current.get("status") or document["status"]),
        }

    def lease_next(
        self,
        worker_id: str,
        lease_seconds: int = 180,
    ) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        locked_until = now + timedelta(seconds=int(lease_seconds))
        query = {
            "status": {"$in": ["pending", "retry"]},
            "$or": [{"locked_until": None}, {"locked_until": {"$lte": now}}],
        }
        update = {
            "$set": {
                "status": "processing",
                "locked_by": str(worker_id),
                "locked_until": locked_until,
                "started_at": now,
                "updated_at": now,
            }
        }
        return self.collection.find_one_and_update(
            query,
            update,
            sort=[("priority", -1), ("updated_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

    def refresh_lease(self, task_id: str, worker_id: str, lease_seconds: int = 180) -> bool:
        now = _utc_now()
        locked_until = now + timedelta(seconds=int(lease_seconds))
        result = self.collection.update_one(
            {
                "task_id": str(task_id),
                "status": "processing",
                "locked_by": str(worker_id),
                "locked_until": {"$gt": now},
            },
            {
                "$set": {
                    "locked_until": locked_until,
                    "heartbeat_at": now,
                    "updated_at": now,
                }
            },
        )
        return result.modified_count == 1

    def mark_success(self, task_id: str, worker_id: str, meta: Optional[Dict[str, Any]] = None) -> bool:
        now = _utc_now()
        result = self.collection.update_one(
            {
                "task_id": str(task_id),
                "status": "processing",
                "locked_by": str(worker_id),
                "locked_until": {"$gt": now},
            },
            {
                "$set": {
                    "status": "success",
                    "locked_by": None,
                    "locked_until": None,
                    "last_error": None,
                    "meta": meta or {},
                    "finished_at": now,
                    "updated_at": now,
                }
            },
        )
        return result.modified_count == 1

    def mark_failed(
        self,
        task_id: str,
        worker_id: str,
        error: str,
        retryable: bool = True,
    ) -> bool:
        now = _utc_now()
        task = self.collection.find_one(
            {
                "task_id": str(task_id),
                "status": "processing",
                "locked_by": str(worker_id),
                "locked_until": {"$gt": now},
            }
        ) or {}
        if not task:
            return False
        retry_count = int(task.get("retry_count", 0)) + 1
        max_retries = int(task.get("max_retries", 3))
        status = "retry" if retryable and retry_count <= max_retries else "dead"
        result = self.collection.update_one(
            {
                "task_id": str(task_id),
                "status": "processing",
                "locked_by": str(worker_id),
                "locked_until": {"$gt": now},
            },
            {
                "$set": {
                    "status": status,
                    "locked_by": None,
                    "locked_until": None,
                    "last_error": str(error)[:800],
                    "finished_at": now,
                    "updated_at": now,
                },
                "$inc": {"retry_count": 1},
            },
        )
        return result.modified_count == 1

    def reset_task(self, url: str) -> bool:
        result = self.collection.update_one(
            {"url": str(url), "status": {"$in": ["dead", "success", "failed"]}},
            {
                "$set": {
                    "status": "pending",
                    "retry_count": 0,
                    "locked_by": None,
                    "locked_until": None,
                    "last_error": None,
                    "updated_at": _utc_now(),
                },
            },
        )
        return result.modified_count == 1

    def counts_by_status(self) -> Dict[str, int]:
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        results = {row["_id"]: int(row["count"]) for row in self.collection.aggregate(pipeline)}
        return results
