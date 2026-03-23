import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.models.account_raw import CollectionErrorCode, CollectionStatus
from src.storage.mongo_store import MongoRawStore


class AccountCollector:
    def __init__(
        self,
        raw_store: Optional[MongoRawStore] = None,
        throttle_seconds: float = 0.6,
        max_retries: int = 2,
    ):
        self.raw_store = raw_store or MongoRawStore()
        self.throttle_seconds = throttle_seconds
        self.max_retries = max_retries

    async def collect(
        self,
        account_id: str,
        profile_loader: Callable[[], Awaitable[Dict[str, Any]]],
        likes_loader: Optional[Callable[[], Awaitable[List[Dict[str, Any]]]]] = None,
        favorites_loader: Optional[Callable[[], Awaitable[List[Dict[str, Any]]]]] = None,
        follows_loader: Optional[Callable[[], Awaitable[List[Dict[str, Any]]]]] = None,
        collections_loader: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        bundle: Dict[str, Any] = {
            "account_id": str(account_id),
            "collection_window": {
                "start_at": now_iso,
                "end_at": now_iso,
                "collected_at": now_iso,
            },
            "collection_log": [],
            "profile": {},
            "posts": [],
            "likes": [],
            "favorites": [],
            "follows": [],
            "collections": {"folders": [], "items": []},
            "source": source or "account_collector",
        }
        failures: List[Dict[str, Any]] = []
        retry_count = 0

        profile_payload, profile_failure, profile_retry = await self._with_retry(profile_loader, "profile")
        retry_count += profile_retry
        if profile_failure:
            failures.append(profile_failure)
        if profile_payload:
            bundle["profile"] = profile_payload.get("profile", {}) or {}
            bundle["posts"] = profile_payload.get("posts", []) or []
            bundle["collection_log"].append({"dimension": "profile_posts", "status": "success"})
        else:
            bundle["collection_log"].append({"dimension": "profile_posts", "status": "failed"})

        likes_payload, likes_failure, likes_retry = await self._with_retry(
            likes_loader or self._empty_dimension_loader, "likes"
        )
        retry_count += likes_retry
        if likes_failure:
            failures.append(likes_failure)
        bundle["likes"] = likes_payload or []
        bundle["collection_log"].append(
            {"dimension": "likes", "status": "success" if not likes_failure else "failed"}
        )

        favorites_payload, favorites_failure, favorites_retry = await self._with_retry(
            favorites_loader or self._empty_dimension_loader, "favorites"
        )
        retry_count += favorites_retry
        if favorites_failure:
            failures.append(favorites_failure)
        bundle["favorites"] = favorites_payload or []
        bundle["collection_log"].append(
            {"dimension": "favorites", "status": "success" if not favorites_failure else "failed"}
        )

        follows_payload, follows_failure, follows_retry = await self._with_retry(
            follows_loader or self._empty_dimension_loader, "follows"
        )
        retry_count += follows_retry
        if follows_failure:
            failures.append(follows_failure)
        bundle["follows"] = follows_payload or []
        bundle["collection_log"].append(
            {"dimension": "follows", "status": "success" if not follows_failure else "failed"}
        )

        collections_payload, collections_failure, collections_retry = await self._with_retry(
            collections_loader or self._empty_collections_loader, "collections"
        )
        retry_count += collections_retry
        if collections_failure:
            failures.append(collections_failure)
        bundle["collections"] = collections_payload or {"folders": [], "items": []}
        bundle["collection_log"].append(
            {"dimension": "collections", "status": "success" if not collections_failure else "failed"}
        )

        status = CollectionStatus.SUCCESS.value
        if failures and not bundle["profile"]:
            status = CollectionStatus.FAILED.value
        elif failures:
            status = CollectionStatus.PARTIAL.value

        primary_failure = failures[0] if failures else {}
        account_id_written = self.raw_store.upsert_profile_bundle(
            bundle=bundle,
            collection_status=status,
            error_code=primary_failure.get("error_code"),
            error_message=primary_failure.get("error_message"),
            retryable=bool(failures),
            retry_count=retry_count,
            max_retries=self.max_retries,
            source=source,
        )
        return {
            "account_id": account_id_written,
            "collection_status": status,
            "failures": failures,
            "retry_count": retry_count,
        }

    async def _with_retry(
        self,
        loader: Callable[[], Awaitable[Any]],
        dimension: str,
    ) -> tuple[Any, Optional[Dict[str, str]], int]:
        retries = 0
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                payload = await loader()
                return payload, None, retries
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                retries += 1
                await asyncio.sleep(self.throttle_seconds * (attempt + 1))
        failure = {
            "dimension": dimension,
            "error_code": self._classify_error(last_error),
            "error_message": str(last_error) if last_error else "unknown error",
        }
        return None, failure, retries

    async def _empty_dimension_loader(self) -> List[Dict[str, Any]]:
        await asyncio.sleep(self.throttle_seconds)
        return []

    async def _empty_collections_loader(self) -> Dict[str, Any]:
        await asyncio.sleep(self.throttle_seconds)
        return {"folders": [], "items": []}

    def _classify_error(self, error: Optional[Exception]) -> str:
        if not error:
            return CollectionErrorCode.UNKNOWN.value
        text = str(error).lower()
        if "rate" in text or "429" in text:
            return CollectionErrorCode.RATE_LIMITED.value
        if "login" in text or "auth" in text:
            return CollectionErrorCode.LOGIN_REQUIRED.value
        if "parse" in text or "json" in text:
            return CollectionErrorCode.PARSE_ERROR.value
        if "timeout" in text or "network" in text or "connection" in text:
            return CollectionErrorCode.NETWORK_ERROR.value
        return CollectionErrorCode.UNKNOWN.value
