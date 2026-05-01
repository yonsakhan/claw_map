import json
import os
import sys

sys.path.append(os.getcwd())
from src.storage.mongo_store import MongoRawStore


def _clean_url(value: str) -> str:
    return (value or "").strip().strip("`").strip("´").strip("｀").strip('"').strip("'").strip()


def _preprocess_bundle(bundle: dict) -> dict:
    """兼容 keyword_scout 输出：清理 URL 里的反引号，并尽量保证字段结构稳定。"""
    if not isinstance(bundle, dict):
        return {}
    profile = bundle.get("profile")
    if isinstance(profile, dict):
        if profile.get("profile_url"):
            profile["profile_url"] = _clean_url(profile["profile_url"])
    posts = bundle.get("posts")
    if isinstance(posts, list):
        for post in posts:
            if not isinstance(post, dict):
                continue
            if post.get("url"):
                post["url"] = _clean_url(post["url"])
            detail = post.get("detail")
            if isinstance(detail, dict) and detail.get("url"):
                detail["url"] = _clean_url(detail["url"])
            # image_urls 仅做简单去空
            if isinstance(detail, dict) and isinstance(detail.get("image_urls"), list):
                detail["image_urls"] = [u for u in detail["image_urls"] if isinstance(u, str) and u.strip()]
    if bundle.get("url"):
        bundle["url"] = _clean_url(bundle["url"])
    return bundle


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
            bundle = _preprocess_bundle(bundle)
            account_id = store.upsert_profile_bundle(bundle, source=file_path)
            if account_id:
                inserted += 1
            else:
                skipped += 1
    print(f"Ingested/Updated: {inserted}")
    print(f"Skipped: {skipped}")
    print(f"Mongo Collection Count: {store.count()}")


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "dummy_data.jsonl"
    ingest(file_path)
