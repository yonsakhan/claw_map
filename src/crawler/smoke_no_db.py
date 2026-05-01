import argparse
import asyncio
import json
import os
from typing import Any, Dict

from src.crawler.errors import CrawlError
from src.crawler.xiaohongshu_scraper import XiaohongshuScraper


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="无数据库依赖的采集冒烟测试")
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.xiaohongshu.com/user/profile/5b15392b4260905102559902",
        help="小红书用户主页 URL",
    )
    parser.add_argument("--headless", action="store_true", help="使用无头模式（默认 False，便于人工观察）")
    parser.add_argument(
        "--auto-login",
        action="store_true",
        help="遇到 login_required 时，自动弹出浏览器引导登录并重试一次（仅在 headless=False 时有效）",
    )
    parser.add_argument(
        "--with-collections",
        action="store_true",
        help="是否额外采集收藏页（更容易触发拦截，默认关闭）",
    )
    parser.add_argument("--out", type=str, default="reports/smoke_no_db.json", help="输出报告路径")
    return parser.parse_args()


def _normalize_cli_url(url: str) -> str:
    # 兼容用户习惯把 URL 写成 `...` 或 "..." / '...'
    # 另外如果还保留 <id> 占位符，直接提示用户替换成真实 id。
    candidate = (url or "").strip().strip("`").strip("´").strip("｀").strip('"').strip("'").strip()
    if "<id>" in candidate or ("<" in candidate and ">" in candidate and "user/profile" in candidate):
        # 只对 profile URL 做强提示，避免误伤其他 URL（比如搜索 URL 的 query 里可能含 < >）。
        raise ValueError("请把 URL 里的 <id> 替换为真实的小红书用户 id（例如 5b15392b4260905102559902）")
    return candidate


async def _run(url: str, headless: bool, with_collections: bool, auto_login: bool) -> Dict[str, Any]:
    normalized_url = _normalize_cli_url(url)
    scraper = XiaohongshuScraper(headless=headless)
    report: Dict[str, Any] = {
        "url": normalized_url,
        "headless": headless,
        "with_collections": with_collections,
        "status": "unknown",
        "error_code": None,
        "error_message": None,
        "profile_keys": [],
        "posts_count": 0,
        "collections_items_count": 0,
    }
    try:
        # 你需要的体验：进入网站后第一件事先确认登录态；未登录就等待你登录成功后再继续。
        if auto_login and (not headless):
            await scraper.ensure_logged_in()
        dimensions = await scraper.fetch_account_dimensions(normalized_url)
        if not dimensions:
            report["status"] = "failed"
            report["error_message"] = "fetch_account_dimensions returned None"
            return report
        profile = dimensions.get("profile", {}) or {}
        posts = dimensions.get("posts", []) or []
        report["profile_keys"] = sorted(list(profile.keys()))
        report["posts_count"] = len(posts)

        if with_collections:
            collections = await scraper.fetch_collections(normalized_url)
            items = (collections or {}).get("items") or []
            report["collections_items_count"] = len(items)

        report["status"] = "ok"
        return report
    except CrawlError as exc:
        report["status"] = "blocked" if exc.error_code else "failed"
        report["error_code"] = exc.error_code
        report["error_message"] = str(exc)
        # 你希望的体验：如果 Cookie/状态失效导致 login_required，则自动触发一次“手动登录”并重试。
        # 仅在 headless=False 时启用，否则无法让你在弹窗里完成登录。
        if auto_login and (not headless) and exc.error_code == "login_required":
            try:
                await scraper.login_and_save_state()
                dimensions = await scraper.fetch_account_dimensions(normalized_url)
                if dimensions:
                    profile = dimensions.get("profile", {}) or {}
                    posts = dimensions.get("posts", []) or []
                    report["profile_keys"] = sorted(list(profile.keys()))
                    report["posts_count"] = len(posts)
                    if with_collections:
                        collections = await scraper.fetch_collections(normalized_url)
                        items = (collections or {}).get("items") or []
                        report["collections_items_count"] = len(items)
                    report["status"] = "ok"
                    report["error_code"] = None
                    report["error_message"] = None
            except Exception as login_exc:
                report["error_message"] = f"{report['error_message']} | auto-login retry failed: {login_exc}"
        return report
    except Exception as exc:
        report["status"] = "failed"
        report["error_message"] = str(exc)
        return report


def main():
    args = _parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    report = asyncio.run(
        _run(
            args.url,
            headless=bool(args.headless),
            with_collections=bool(args.with_collections),
            auto_login=bool(args.auto_login),
        )
    )
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
