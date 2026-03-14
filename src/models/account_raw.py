from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CollectionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class CollectionErrorCode(str, Enum):
    NONE = "none"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    LOGIN_REQUIRED = "login_required"
    PARSE_ERROR = "parse_error"
    DATA_VALIDATION_ERROR = "data_validation_error"
    UNKNOWN = "unknown"


@dataclass
class RetryMarker:
    retryable: bool = False
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retryable": self.retryable,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "next_retry_at": self.next_retry_at,
        }


@dataclass
class FailureInfo:
    error_code: str = CollectionErrorCode.NONE.value
    error_message: Optional[str] = None
    failed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "failed_at": self.failed_at,
        }


def _normalize_status(status: Optional[str]) -> str:
    if not status:
        return CollectionStatus.SUCCESS.value
    valid_values = {item.value for item in CollectionStatus}
    if status in valid_values:
        return status
    return CollectionStatus.SUCCESS.value


def _normalize_error_code(error_code: Optional[str]) -> str:
    if not error_code:
        return CollectionErrorCode.NONE.value
    valid_values = {item.value for item in CollectionErrorCode}
    if error_code in valid_values:
        return error_code
    return CollectionErrorCode.UNKNOWN.value


def _resolve_account_id(bundle: Dict[str, Any]) -> str:
    profile = bundle.get("profile", {})
    account_id = bundle.get("account_id") or profile.get("id")
    return str(account_id).strip() if account_id is not None else ""


def build_account_raw_document(
    bundle: Dict[str, Any],
    collection_status: Optional[str] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    retryable: Optional[bool] = None,
    retry_count: Optional[int] = None,
    max_retries: int = 3,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    account_id = _resolve_account_id(bundle)
    if not account_id:
        raise ValueError("missing account_id")

    status = _normalize_status(collection_status or bundle.get("collection_status"))
    normalized_error_code = _normalize_error_code(error_code)
    if normalized_error_code == CollectionErrorCode.NONE.value:
        normalized_error_code = _normalize_error_code(bundle.get("failure", {}).get("error_code"))
    if status == CollectionStatus.FAILED.value and normalized_error_code == CollectionErrorCode.NONE.value:
        normalized_error_code = CollectionErrorCode.UNKNOWN.value

    profile = bundle.get("profile", {}) or {}
    posts = bundle.get("posts", []) or []
    likes = bundle.get("likes", []) or []
    favorites = bundle.get("favorites", []) or []
    follows = bundle.get("follows", []) or []
    now_iso = _now_iso()

    window = bundle.get("collection_window", {}) or {}
    start_at = window.get("start_at") or bundle.get("window_start") or now_iso
    end_at = window.get("end_at") or bundle.get("window_end") or now_iso
    collected_at = window.get("collected_at") or bundle.get("collected_at") or now_iso

    bundle_retry = bundle.get("retry", {}) or {}
    retry_marker = RetryMarker(
        retryable=retryable if retryable is not None else bundle_retry.get("retryable", status in {CollectionStatus.FAILED.value, CollectionStatus.PARTIAL.value}),
        retry_count=retry_count if retry_count is not None else int(bundle_retry.get("retry_count", 0)),
        max_retries=int(bundle_retry.get("max_retries", max_retries)),
        next_retry_at=bundle_retry.get("next_retry_at"),
    )

    failure = FailureInfo(
        error_code=normalized_error_code,
        error_message=error_message or bundle.get("failure", {}).get("error_message"),
        failed_at=now_iso if status == CollectionStatus.FAILED.value else bundle.get("failure", {}).get("failed_at"),
    )

    collection_log = bundle.get("collection_log", []) or []

    return {
        "account_id": account_id,
        "schema_version": "v2",
        "collection_status": status,
        "collection_window": {
            "start_at": start_at,
            "end_at": end_at,
            "collected_at": collected_at,
        },
        "retry": retry_marker.to_dict(),
        "failure": failure.to_dict(),
        "raw_data": {
            "profile": profile,
            "posts": posts,
            "likes": likes,
            "favorites": favorites,
            "follows": follows,
        },
        "stats": {
            "posts_count": len(posts),
            "likes_count": len(likes),
            "favorites_count": len(favorites),
            "follows_count": len(follows),
        },
        "collection_log": collection_log,
        "source": source or bundle.get("source"),
        "updated_at": now_iso,
    }
