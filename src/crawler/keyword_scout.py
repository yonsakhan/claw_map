import argparse
import asyncio
import json
import os
import random
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from src.crawler.errors import CrawlError
from src.crawler.xiaohongshu_scraper import XiaohongshuScraper


def _clean_url(value: str) -> str:
    # 兼容用户复制/日志里出现的 `...`，避免写入结果文件后影响后续解析
    return (value or "").strip().strip("`").strip("´").strip("｀").strip('"').strip("'").strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="关键词人群侦察：搜索关键词 → 收集账号 URL → 拉取主页+前10笔记")
    parser.add_argument(
        "--keyword",
        type=str,
        default="",
        help="搜索关键词（例如：母婴室 / 亲子公园 / 托育）。如果不确定搜索页 URL，建议先手动在浏览器搜索一次，再把地址栏 URL 作为 --search-url 传入。",
    )
    parser.add_argument(
        "--search-url",
        type=str,
        default="",
        help="小红书搜索结果页 URL（推荐：在浏览器里搜索关键词后复制地址栏）。",
    )
    parser.add_argument("--limit", type=int, default=100, help="最多采样账号数（建议分批跑，比如 20/50/100）")
    parser.add_argument("--headless", action="store_true", help="无头模式（默认 False，便于观察登录/风控）")
    parser.add_argument(
        "--auto-login",
        action="store_true",
        help="运行前先检查是否已登录；若未登录则弹出浏览器等待你完成登录（仅 headless=False 时有效）",
    )
    parser.add_argument(
        "--notes-per-user",
        type=int,
        default=0,
        help="对每个账号额外抓取多少条笔记详情（会打开笔记页面，触发风控概率更高；建议 1~3 开始）。默认 0=不抓详情。",
    )
    parser.add_argument(
        "--comments-per-note",
        type=int,
        default=0,
        help="每条笔记抓取多少条评论文本（粗粒度，默认 0=不抓）。",
    )
    parser.add_argument(
        "--stop-on-rate-limit",
        action="store_true",
        help="一旦检测到访问频繁/风控（rate_limited）就立即停止，避免继续触发警告（推荐开启）。",
    )
    parser.add_argument(
        "--stop-on-login-required",
        action="store_true",
        help="一旦出现扫码/登录验证（login_required）就立即停止，避免账号风险（推荐开启）。",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="输出文件路径（jsonl）。默认写到 reports/keyword_scout_<keyword>_<ts>.jsonl",
    )
    return parser.parse_args()


def _build_search_url(keyword: str) -> str:
    kw = (keyword or "").strip()
    if not kw:
        return ""
    # 注意：小红书搜索页形态可能调整；如果这个 URL 不可用，请优先使用 --search-url（手动复制地址栏）。
    return f"https://www.xiaohongshu.com/search_result?keyword={quote(kw)}"


def _default_out_path(keyword: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw = (keyword or "search").strip().replace("/", "_")[:30]
    return os.path.join("reports", f"keyword_scout_{safe_kw}_{ts}.jsonl")


async def _run(
    search_url: str,
    headless: bool,
    limit: int,
    out_path: str,
    notes_per_user: int,
    comments_per_note: int,
    stop_on_rate_limit: bool,
    auto_login: bool,
    stop_on_login_required: bool,
) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    scraper = XiaohongshuScraper(headless=headless)
    if auto_login and (not headless):
        await scraper.ensure_logged_in()

    # 1) 从搜索页收集 profile URL
    profile_urls = await scraper.collect_accounts_from_search(search_url, limit=limit)
    profile_urls = [u for u in profile_urls if u]

    summary: Dict[str, Any] = {
        "search_url": search_url,
        "limit": limit,
        "collected_profile_urls": len(profile_urls),
        "fetched_ok": 0,
        "blocked": 0,
        "failed": 0,
        "out": out_path,
    }

    # 2) 逐个拉取主页 + 前10笔记（尽量控频）
    with open(out_path, "w", encoding="utf-8") as f:
        for idx, url in enumerate(profile_urls, start=1):
            clean_profile_url = _clean_url(url)
            record: Dict[str, Any] = {
                "index": idx,
                "url": clean_profile_url,
                "status": "unknown",
                "error_code": None,
                "error": None,
            }
            try:
                payload = await scraper.fetch_account_dimensions(clean_profile_url)
                if not payload:
                    record["status"] = "failed"
                    record["error"] = "fetch_account_dimensions returned None"
                    summary["failed"] += 1
                else:
                    record["status"] = "ok"
                    record["account_id"] = payload.get("account_id")
                    record["profile"] = payload.get("profile") or {}
                    posts = payload.get("posts") or []
                    # 再清理一次 URL（避免结果里残留 `...`）
                    for post in posts:
                        if isinstance(post, dict) and post.get("url"):
                            post["url"] = _clean_url(post["url"])
                    record["posts"] = posts
                    # 可选：抓取笔记详情（打开笔记页）
                    if notes_per_user > 0 and posts:
                        for post in posts[: max(0, int(notes_per_user))]:
                            note_url = (post or {}).get("url") or ""
                            if not note_url:
                                continue
                            try:
                                detail = await scraper.fetch_note_detail(
                                    _clean_url(note_url),
                                    comments_limit=int(comments_per_note),
                                )
                                # 将笔记详情“嵌入”到 posts 里，便于直接入库到 Mongo（raw_data.posts）
                                # 注意：这里只保存图片 URL + 文案 + 少量评论文本（可选），不下载图片二进制，降低风险与体积。
                                if isinstance(post, dict):
                                    post["detail"] = detail
                            except CrawlError as note_exc:
                                # 笔记详情页更容易触发扫码/频控；这里不把整个账号采集判失败，但要尽早止损。
                                if isinstance(post, dict):
                                    post["detail_error_code"] = note_exc.error_code
                                    post["detail_error"] = str(note_exc)
                                if note_exc.error_code == "rate_limited" and stop_on_rate_limit:
                                    record["status"] = "rate_limited"
                                    record["error_code"] = "rate_limited"
                                    record["error"] = str(note_exc)
                                    summary["blocked"] += 1
                                    summary["stopped_reason"] = "rate_limited(note_detail)"
                                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                                    f.flush()
                                    return summary
                                if note_exc.error_code == "login_required" and stop_on_login_required:
                                    record["status"] = "login_required"
                                    record["error_code"] = "login_required"
                                    record["error"] = str(note_exc)
                                    summary["blocked"] += 1
                                    summary["stopped_reason"] = "login_required(note_detail)"
                                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                                    f.flush()
                                    return summary
                            # 控频：打开笔记页很容易风控
                            await asyncio.sleep(random.uniform(4.0, 10.0))
                    summary["fetched_ok"] += 1
            except CrawlError as exc:
                record["error_code"] = exc.error_code
                record["error"] = str(exc)
                if exc.error_code == "rate_limited":
                    record["status"] = "rate_limited"
                    summary["blocked"] += 1
                    # 触发频控：默认直接停止，避免继续触发警告/封禁
                    if stop_on_rate_limit:
                        summary["stopped_reason"] = "rate_limited"
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        f.flush()
                        break
                    # 如果不停止，则做一次较长冷却后继续（不推荐）
                    await asyncio.sleep(random.uniform(10 * 60, 30 * 60))
                elif exc.error_code == "login_required":
                    record["status"] = "login_required"
                    summary["blocked"] += 1
                    if stop_on_login_required:
                        summary["stopped_reason"] = "login_required"
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        f.flush()
                        break
                else:
                    record["status"] = "failed"
                    summary["failed"] += 1
            except Exception as exc:
                record["status"] = "failed"
                record["error"] = str(exc)
                summary["failed"] += 1

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()

            # 正常控频：随机睡眠，避免“访问频繁”
            await asyncio.sleep(random.uniform(3.0, 8.0))

    return summary


def main():
    args = _parse_args()
    keyword = (args.keyword or "").strip()
    # 统一清理用户输入里的反引号/引号，避免 URL 被当成字面文本（你之前日志里的 `https://...` 就会导致解析异常）
    search_url = (
        (args.search_url or "")
        .strip()
        .strip("`")
        .strip("´")
        .strip("｀")
        .strip('"')
        .strip("'")
        .strip()
    )
    if not search_url:
        search_url = _build_search_url(keyword)
    search_url = (search_url or "").strip().strip("`").strip("´").strip("｀").strip('"').strip("'").strip()
    if not search_url:
        raise SystemExit("请提供 --search-url（推荐）或 --keyword。")

    out_path = (args.out or "").strip()
    if not out_path:
        out_path = _default_out_path(keyword or "search")

    summary = asyncio.run(
        _run(
            search_url,
            headless=bool(args.headless),
            limit=int(args.limit),
            out_path=out_path,
            notes_per_user=int(args.notes_per_user),
            comments_per_note=int(args.comments_per_note),
            stop_on_rate_limit=bool(args.stop_on_rate_limit),
            auto_login=bool(args.auto_login),
            stop_on_login_required=bool(args.stop_on_login_required),
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
