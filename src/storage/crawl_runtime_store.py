from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import MongoClient

from src.config import settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CrawlRuntimeStore:
    def __init__(self):
        self.client = MongoClient(settings.mongo_url)
        self.collection = self.client[settings.mongo_db][settings.mongo_runtime_collection]
        self.key_rate_limit_cooldown = "xhs_rate_limit_cooldown"

    def get_rate_limit_cooldown_until_epoch(self) -> Optional[float]:
        try:
            doc = self.collection.find_one({"_id": self.key_rate_limit_cooldown}, {"cooldown_until": 1}) or {}
            cooldown_until = doc.get("cooldown_until")
            if not isinstance(cooldown_until, datetime):
                return None
            if cooldown_until.tzinfo is None:
                cooldown_until = cooldown_until.replace(tzinfo=timezone.utc)
            return cooldown_until.timestamp()
        except Exception:
            return None

    def set_rate_limit_cooldown(self, seconds: int, reason: str = "", source: str = "") -> Optional[float]:
        now = _utc_now()
        cooldown_until = now + timedelta(seconds=max(0, int(seconds)))
        try:
            self.collection.update_one(
                {"_id": self.key_rate_limit_cooldown},
                {
                    "$max": {"cooldown_until": cooldown_until},
                    "$set": {
                        "updated_at": now,
                        "reason": str(reason or ""),
                        "source": str(source or ""),
                    },
                },
                upsert=True,
            )
            return cooldown_until.timestamp()
        except Exception:
            return None
