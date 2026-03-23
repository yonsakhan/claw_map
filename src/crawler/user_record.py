from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


PROFILE_REQUIRED_KEYS = [
    "display_name",
    "xhs_id",
    "bio",
    "follow_count",
    "fans_count",
    "likes_favorites_count",
    "profile_url",
]

COLLECTIONS_REQUIRED_KEYS = [
    "folders",
    "items",
]


def build_user_record(
    profile: Dict[str, Any],
    collections: Dict[str, Any],
    source_entry: str,
) -> Dict[str, Any]:
    record = {
        "schema_version": "v1",
        "captured_at": _utc_now_iso(),
        "source_entry": str(source_entry or ""),
        "profile": profile or {},
        "collections": collections or {"folders": [], "items": []},
    }
    return record


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False


def calculate_missing_rate(record: Dict[str, Any]) -> Tuple[float, List[str]]:
    missing_keys: List[str] = []
    profile = record.get("profile", {}) or {}
    for key in PROFILE_REQUIRED_KEYS:
        if _is_missing(profile.get(key)):
            missing_keys.append(f"profile.{key}")

    collections = record.get("collections", {}) or {}
    for key in COLLECTIONS_REQUIRED_KEYS:
        if _is_missing(collections.get(key)):
            missing_keys.append(f"collections.{key}")

    total_required = len(PROFILE_REQUIRED_KEYS) + len(COLLECTIONS_REQUIRED_KEYS)
    rate = round(len(missing_keys) / total_required, 4) if total_required else 0.0
    return rate, missing_keys


def flatten_for_csv(record: Dict[str, Any]) -> Dict[str, Any]:
    profile = record.get("profile", {}) or {}
    collections = record.get("collections", {}) or {}
    folders = collections.get("folders") or []
    items = collections.get("items") or []
    return {
        "captured_at": record.get("captured_at"),
        "source_entry": record.get("source_entry"),
        "display_name": profile.get("display_name"),
        "xhs_id": profile.get("xhs_id"),
        "ip_location": profile.get("ip_location"),
        "location": profile.get("location"),
        "bio": profile.get("bio"),
        "follow_count": profile.get("follow_count"),
        "fans_count": profile.get("fans_count"),
        "likes_favorites_count": profile.get("likes_favorites_count"),
        "profile_url": profile.get("profile_url"),
        "folders_count": len(folders),
        "items_count": len(items),
    }

