"""关键词定向采集 — 按研究主题搜索小红书帖子，提取发帖用户 profile。

用法：
    python -m scripts.keyword_crawl                    # 用默认关键词采集
    python -m scripts.keyword_crawl --limit 50         # 每个关键词最多 50 个用户
    python -m scripts.keyword_crawl --keywords "备孕,怀孕"  # 指定关键词
"""

import argparse
import asyncio
import json
import logging
import os
import re
import time
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("KeywordCrawl")

STATE_PATH = "src/storage/xhs_state.json"
OUTPUT_DIR = "data/profiles"

# 研究主题关键词：生育友好型空间
DEFAULT_KEYWORDS = [
    "备孕",
    "怀孕日记",
    "孕期日常",
    "宝妈日常",
    "遛娃好去处",
    "带娃出行",
    "母婴室",
    "产后恢复",
    "育儿嫂",
    "幼儿园选择",
    "托育",
    "生育补贴",
    "产假",
    "孕妇友好",
    "亲子空间",
]


def parse_profile_text(body_text: str) -> dict:
    """从页面 body 文本中解析 profile 信息。"""
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]
    joined = "\n".join(lines)

    account_match = re.search(r"小红书号[:：]\s*([0-9A-Za-z_-]+)", joined)
    ip_match = re.search(r"IP属地[:：]\s*([^\n\r]+)", joined)
    follow_match = re.search(r"(\d+)\s*关注", joined)
    fans_match = re.search(r"(\d+)\s*粉丝", joined)
    likes_match = re.search(r"(\d+)\s*获赞与收藏", joined)
    note_match = re.search(r"笔记[・·\s]*([0-9]+)", joined)

    account_idx = next((i for i, l in enumerate(lines) if "小红书号" in l), -1)
    name = ""
    noise = {"创作中心", "业务合作", "发现", "直播", "发布", "通知", "我", "搜索小红书",
             "关注", "笔记", "收藏", "行吟信息科技", "小红书", "更多", "活动", "电话：9501-3888"}
    if account_idx > 0:
        for l in lines[:account_idx]:
            if l in noise or l.startswith("©") or l.startswith("地址：") or l.startswith("电话："):
                continue
            if any(kw in l for kw in ["公司", "有限", "集团", "股份", "ICP", "备案", "公安网", "马当路"]):
                continue
            if len(l) >= 2 and len(l) <= 30:
                name = l
                break

    stats_idx = next((i for i, l in enumerate(lines) if re.match(r"^\d+\s*(关注|粉丝)", l)), len(lines))
    bio = ""
    if account_idx >= 0 and stats_idx > account_idx + 1:
        bio_parts = [l for l in lines[account_idx + 1:stats_idx]
                     if l not in {"关注", "笔记", "收藏"} and "IP属地" not in l]
        bio = " ".join(bio_parts[:3])

    return {
        "display_name": name,
        "xhs_id": account_match.group(1) if account_match else "",
        "ip_location": ip_match.group(1).strip() if ip_match else "",
        "bio": bio,
        "follow_count": int(follow_match.group(1)) if follow_match else 0,
        "fans_count": int(fans_match.group(1)) if fans_match else 0,
        "likes_favorites_count": int(likes_match.group(1)) if likes_match else 0,
        "note_count": int(note_match.group(1)) if note_match else 0,
    }


async def extract_posts(page: Page) -> list[dict]:
    """从 profile 页面提取帖子列表。"""
    for _ in range(3):
        await page.evaluate("window.scrollBy(0, 600)")
        await page.wait_for_timeout(1000)

    cards = await page.locator("section.note-item, section[class*='note-item']").all()
    posts = []
    for card in cards:
        try:
            text = (await card.inner_text()).strip()
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if not lines:
                continue
            link = card.locator("a").first
            href = await link.get_attribute("href") or ""
            post_id = ""
            if "/explore/" in href:
                post_id = href.split("/explore/")[-1].split("?")[0]
            title = lines[0] if lines else ""
            likes = 0
            for l in reversed(lines):
                if l.isdigit():
                    likes = int(l)
                    break
            posts.append({
                "post_id": post_id,
                "title": title,
                "likes": likes,
                "url": f"https://www.xiaohongshu.com/explore/{post_id}" if post_id else "",
            })
        except Exception:
            continue
    return posts


async def fetch_profile(page: Page, url: str, timeout: int = 20000) -> Optional[dict]:
    """抓取单个 profile 页面。"""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(2000)

        current_url = page.url
        if "login" in current_url or "captcha" in current_url:
            logger.warning("被拦截: %s", current_url[:80])
            logger.info("请在浏览器中扫码验证，等待最多 90 秒...")
            for i in range(90):
                await asyncio.sleep(1)
                if "login" not in page.url and "captcha" not in page.url:
                    logger.info("扫码成功，继续采集")
                    await page.wait_for_timeout(2000)
                    break
                if i % 15 == 0 and i > 0:
                    logger.info("等待扫码... (%ds)", i)
            else:
                logger.warning("扫码超时，跳过")
                return None
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(2000)

        body = await page.locator("body").inner_text()
        if "小红书号" not in body:
            return None

        profile = parse_profile_text(body)
        profile["profile_url"] = url
        profile["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        posts = await extract_posts(page)
        profile["posts"] = posts
        profile["post_count"] = len(posts)
        return profile

    except Exception as e:
        logger.error("抓取失败: %s - %s", url[:60], e)
        return None


async def search_keyword(page: Page, keyword: str, max_users: int) -> list[dict]:
    """搜索关键词，返回帖子中发现的用户信息列表。"""
    search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
    logger.info("搜索: %s", keyword)
    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    # 检查是否被拦截
    if "login" in page.url or "captcha" in page.url:
        logger.warning("搜索被拦截，请扫码...")
        for i in range(90):
            await asyncio.sleep(1)
            if "login" not in page.url and "captcha" not in page.url:
                break
            if i % 15 == 0 and i > 0:
                logger.info("等待扫码... (%ds)", i)
        else:
            logger.warning("扫码超时，跳过关键词: %s", keyword)
            return []

    # 滚动加载更多结果
    for _ in range(5):
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(1500)

    # 提取帖子中的用户链接
    anchors = await page.locator('a[href*="/user/profile/"]').all()
    seen = set()
    users = []
    for a in anchors:
        try:
            href = await a.get_attribute("href") or ""
            m = re.search(r"/user/profile/([a-f0-9]+)", href)
            if not m or m.group(1) in seen:
                continue
            pid = m.group(1)
            seen.add(pid)

            # 尝试提取帖子标题
            parent = a.locator("xpath=ancestor::section | xpath=ancestor::div[contains(@class,'note-item')]").first
            title = ""
            try:
                title_text = await parent.inner_text()
                title_lines = [l.strip() for l in title_text.splitlines() if l.strip()]
                title = title_lines[0] if title_lines else ""
            except Exception:
                pass

            users.append({
                "user_id": pid,
                "keyword": keyword,
                "sample_title": title[:50],
            })
            if len(users) >= max_users:
                break
        except Exception:
            continue

    logger.info("  发现 %d 个用户", len(users))
    return users


async def run_search(keywords: list[str], limit_per_keyword: int):
    """阶段1：按关键词搜索，收集用户 ID 保存到文件。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(
            storage_state=STATE_PATH if os.path.exists(STATE_PATH) else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = await ctx.new_page()

        # 确保登录
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        body = await page.locator("body").inner_text()
        if len([l for l in body.splitlines() if l.strip()]) <= 30:
            if "login" in page.url or "captcha" in page.url:
                logger.info("需要登录，请扫码...")
                for i in range(120):
                    await asyncio.sleep(1)
                    if "login" not in page.url and "captcha" not in page.url:
                        break
            else:
                logger.error("无法访问小红书")
                await browser.close()
                return

        logger.info("登录态有效")

        all_users = {}
        for kw in keywords:
            users = await search_keyword(page, kw, limit_per_keyword)
            for u in users:
                uid = u["user_id"]
                if uid not in all_users:
                    all_users[uid] = u
                else:
                    existing_kw = all_users[uid].get("keyword", "")
                    if kw not in existing_kw:
                        all_users[uid]["keyword"] = existing_kw + "," + kw
            await asyncio.sleep(5)

        await ctx.storage_state(path=STATE_PATH)
        await browser.close()

    unique_users = list(all_users.values())
    output_path = os.path.join(OUTPUT_DIR, f"search_users_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_users, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"搜索完成！发现 {len(unique_users)} 个独立用户")
    print(f"用户列表保存到: {output_path}")
    print(f"下一步: python -m scripts.keyword_crawl --from-file {output_path}")

    # 按关键词统计
    kw_counts = {}
    for u in unique_users:
        for kw in u.get("keyword", "").split(","):
            kw_counts[kw.strip()] = kw_counts.get(kw.strip(), 0) + 1
    print(f"\n关键词分布:")
    for kw, cnt in sorted(kw_counts.items(), key=lambda x: -x[1]):
        print(f"  {kw}: {cnt} 人")


async def run_fetch(users_file: str):
    """阶段2：从文件读取用户 ID，逐个采集 profile。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(users_file, encoding="utf-8") as f:
        unique_users = json.load(f)
    logger.info("从文件加载 %d 个用户", len(unique_users))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(
            storage_state=STATE_PATH if os.path.exists(STATE_PATH) else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = await ctx.new_page()

        # 确保登录
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        body = await page.locator("body").inner_text()
        if len([l for l in body.splitlines() if l.strip()]) <= 30:
            if "login" in page.url or "captcha" in page.url:
                logger.info("需要登录，请扫码...")
                for i in range(120):
                    await asyncio.sleep(1)
                    if "login" not in page.url and "captcha" not in page.url:
                        break
            else:
                logger.error("无法访问小红书")
                await browser.close()
                return

        logger.info("登录态有效，开始采集 profile")

        results = []
        blocked_count = 0
        for i, user in enumerate(unique_users):
            pid = user["user_id"]
            url = f"https://www.xiaohongshu.com/user/profile/{pid}"
            logger.info("[%d/%d] %s (关键词: %s)", i + 1, len(unique_users), pid, user.get("keyword", ""))

            profile = await fetch_profile(page, url)
            if profile:
                profile["search_keyword"] = user.get("keyword", "")
                profile["sample_title"] = user.get("sample_title", "")
                results.append(profile)
                blocked_count = 0
                logger.info("  OK: %s fans=%d posts=%d",
                            profile.get("display_name", "?"),
                            profile.get("fans_count", 0),
                            profile.get("post_count", 0))
            else:
                blocked_count += 1
                logger.info("  跳过")
                if blocked_count >= 3:
                    logger.warning("连续 %d 次被拦截，停止采集", blocked_count)
                    break

            if i < len(unique_users) - 1:
                wait = 10 + (i % 9)
                if blocked_count > 0:
                    wait += 15
                await asyncio.sleep(wait)

            if (i + 1) % 5 == 0:
                await ctx.storage_state(path=STATE_PATH)
                logger.info("已保存登录状态")

        await ctx.storage_state(path=STATE_PATH)
        await browser.close()

    output_path = os.path.join(OUTPUT_DIR, f"keyword_profiles_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"采集完成！成功 {len(results)}/{len(unique_users)}")
    print(f"结果保存到: {output_path}")

    kw_counts = {}
    for r in results:
        for kw in r.get("search_keyword", "").split(","):
            kw = kw.strip()
            if kw:
                kw_counts[kw] = kw_counts.get(kw, 0) + 1
    print(f"\n关键词分布:")
    for kw, cnt in sorted(kw_counts.items(), key=lambda x: -x[1]):
        print(f"  {kw}: {cnt} 人")

    print(f"\n前 10 个用户:")
    for r in results[:10]:
        print(f"  {r.get('display_name', '?'):15s} fans={r.get('fans_count', 0):6d} posts={r.get('post_count', 0):3d}  kw={r.get('search_keyword', '')}")


def main():
    parser = argparse.ArgumentParser(description="关键词定向采集小红书用户")
    parser.add_argument("--keywords", type=str, default=None, help="关键词，逗号分隔")
    parser.add_argument("--limit", type=int, default=20, help="每个关键词最多采集用户数（默认 20）")
    parser.add_argument("--search-only", action="store_true", help="只搜索收集用户 ID，不采集 profile")
    parser.add_argument("--from-file", type=str, default=None, help="从文件读取用户 ID 采集 profile")
    args = parser.parse_args()

    if args.from_file:
        asyncio.run(run_fetch(args.from_file))
    else:
        keywords = args.keywords.split(",") if args.keywords else DEFAULT_KEYWORDS
        asyncio.run(run_search(keywords=keywords, limit_per_keyword=args.limit))


if __name__ == "__main__":
    main()
