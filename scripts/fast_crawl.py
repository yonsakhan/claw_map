"""高效采集脚本 — 持久浏览器会话，直接抓 SSR 渲染的 profile 数据。

原理：小红书 profile 页面数据通过 SSR 渲染在 HTML 中，不需要 API 调用。
保持一个浏览器实例处理所有 URL，避免反复创建/销毁上下文导致 session 失效。

用法：
    source .venv/bin/activate
    python -m scripts.fast_crawl                    # 从首页发现 20 个 profile
    python -m scripts.fast_crawl --limit 50         # 采集 50 个
    python -m scripts.fast_crawl --urls urls.txt    # 从文件读取 URL
    python -m scripts.fast_crawl --headed           # 有界面模式（首次登录用）
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
logger = logging.getLogger("FastCrawl")

STATE_PATH = "src/storage/xhs_state.json"
OUTPUT_DIR = "data/profiles"


def parse_profile_text(body_text: str) -> dict:
    """从页面 body 文本中解析 profile 信息。"""
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]
    joined = "\n".join(lines)

    # 小红书号
    account_match = re.search(r"小红书号[:：]\s*([0-9A-Za-z_-]+)", joined)
    # IP 属地
    ip_match = re.search(r"IP属地[:：]\s*([^\n\r]+)", joined)
    # 统计数据
    follow_match = re.search(r"(\d+)\s*关注", joined)
    fans_match = re.search(r"(\d+)\s*粉丝", joined)
    likes_match = re.search(r"(\d+)\s*获赞与收藏", joined)
    note_match = re.search(r"笔记[・·\s]*([0-9]+)", joined)

    # display_name: 小红书号之前的第一个有效行
    account_idx = next((i for i, l in enumerate(lines) if "小红书号" in l), -1)
    name = ""
    noise = {"创作中心", "业务合作", "发现", "直播", "发布", "通知", "我", "搜索小红书",
             "关注", "笔记", "收藏", "行吟信息科技", "小红书", "更多", "活动", "电话：9501-3888"}
    if account_idx > 0:
        for l in lines[:account_idx]:
            if l in noise or l.startswith("©") or l.startswith("地址：") or l.startswith("电话："):
                continue
            if any(kw in l for kw in ["公司", "有限", "集团", "股份", "ICP", "备案", "公安网"]):
                continue
            if len(l) >= 2 and len(l) <= 30:
                name = l
                break

    # bio: 小红书号和统计之间的内容（排除 IP 属地行）
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


async def ensure_logged_in(ctx: BrowserContext, page: Page) -> bool:
    """确保登录态有效，无效则等待用户扫码。"""
    await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)
    body = await page.locator("body").inner_text()
    lines = [l.strip() for l in body.splitlines() if l.strip()]

    if len(lines) > 30:
        logger.info("登录态有效")
        return True

    # 可能需要登录
    if "login" in page.url or "captcha" in page.url:
        logger.warning("需要登录，请在浏览器中扫码...")
        for i in range(120):
            await asyncio.sleep(1)
            if "login" not in page.url and "captcha" not in page.url:
                logger.info("登录成功！")
                await ctx.storage_state(path=STATE_PATH)
                return True
            if i % 15 == 0 and i > 0:
                logger.info("等待扫码... (%ds)", i)
        logger.error("登录超时")
        return False

    return True


async def extract_posts(page: Page) -> list[dict]:
    """从 profile 页面提取帖子列表。"""
    # 滚动加载帖子
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

            # 提取链接
            link = card.locator("a").first
            href = await link.get_attribute("href") or ""
            post_id = ""
            if "/explore/" in href:
                post_id = href.split("/explore/")[-1].split("?")[0]

            # 标题是第一行，点赞数是最后一行数字
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
    """抓取单个 profile 页面（含帖子列表）。"""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(2000)

        # 检查是否被拦截
        current_url = page.url
        if "login" in current_url or "captcha" in current_url:
            logger.warning("被拦截: %s", current_url[:80])
            logger.info("请在浏览器中扫码验证，等待最多 90 秒...")
            for i in range(90):
                await asyncio.sleep(1)
                new_url = page.url
                if "login" not in new_url and "captcha" not in new_url:
                    logger.info("扫码成功，继续采集")
                    await page.wait_for_timeout(2000)
                    break
                if i % 15 == 0 and i > 0:
                    logger.info("等待扫码... (%ds)", i)
            else:
                logger.warning("扫码超时，跳过此 profile")
                return None
            # 扫码成功后重新导航到目标 URL
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(2000)

        body = await page.locator("body").inner_text()
        if "小红书号" not in body:
            logger.warning("页面无 profile 数据")
            return None

        profile = parse_profile_text(body)
        profile["profile_url"] = url
        profile["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 提取帖子
        posts = await extract_posts(page)
        profile["posts"] = posts
        profile["post_count"] = len(posts)

        return profile

    except Exception as e:
        logger.error("抓取失败: %s - %s", url[:60], e)
        return None


async def discover_profiles(limit: int) -> list[str]:
    """从首页推荐发现 profile URL（用独立的 headless 浏览器）。"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            storage_state=STATE_PATH if os.path.exists(STATE_PATH) else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()
        await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1500)

        anchors = await page.locator('a[href*="/user/profile/"]').all()
        seen = set()
        pids = []
        self_id = "6958829b000000001903644e"
        for a in anchors:
            href = await a.get_attribute("href") or ""
            m = re.search(r"/user/profile/([a-f0-9]+)", href)
            if m and m.group(1) not in seen and m.group(1) != self_id:
                seen.add(m.group(1))
                pids.append(m.group(1))
            if len(pids) >= limit:
                break
        await browser.close()
        return pids


def load_urls(path: str) -> list[str]:
    """从文件读取 URL。"""
    pids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.search(r"/user/profile/([a-f0-9]+)", line)
            if m:
                pids.append(m.group(1))
            elif re.match(r"^[a-f0-9]{24}$", line):
                pids.append(line)
    return pids


async def run(limit: int, urls_file: Optional[str], headed: bool):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        ctx = await browser.new_context(
            storage_state=STATE_PATH if os.path.exists(STATE_PATH) else None,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = await ctx.new_page()

        # 确保登录
        if not await ensure_logged_in(ctx, page):
            await browser.close()
            return

        # 获取 profile 列表
        if urls_file:
            pids = load_urls(urls_file)
            logger.info("从文件读取 %d 个 profile", len(pids))
        else:
            logger.info("正在发现 profile...")
            pids = await discover_profiles(limit)
            logger.info("发现 %d 个 profile", len(pids))

        if not pids:
            logger.warning("没有可采集的 profile")
            await browser.close()
            return

        # 逐个采集
        results = []
        blocked_count = 0
        for i, pid in enumerate(pids):
            url = f"https://www.xiaohongshu.com/user/profile/{pid}"
            logger.info("[%d/%d] %s", i + 1, len(pids), pid)

            profile = await fetch_profile(page, url)
            if profile:
                results.append(profile)
                blocked_count = 0
                logger.info("  OK: %s fans=%d posts=%d",
                            profile.get("display_name", "?"),
                            profile.get("fans_count", 0),
                            profile.get("post_count", 0))
            else:
                blocked_count += 1
                logger.info("  跳过（被拦截）")
                # 连续被拦截 3 次，说明 session 已失效，提前结束
                if blocked_count >= 3:
                    logger.warning("连续 %d 次被拦截，提前结束采集", blocked_count)
                    break

            # 间隔 10-18 秒（逐步增加）
            if i < len(pids) - 1:
                wait = 10 + (i % 9)  # 10-18 秒
                if blocked_count > 0:
                    wait += 15  # 遇到验证码后额外等待
                logger.info("  等待 %ds...", wait)
                await asyncio.sleep(wait)

            # 每 5 个保存一次状态
            if (i + 1) % 5 == 0:
                await ctx.storage_state(path=STATE_PATH)
                logger.info("已保存登录状态")

        # 保存最终状态
        await ctx.storage_state(path=STATE_PATH)
        await browser.close()

    # 保存结果
    output_path = os.path.join(OUTPUT_DIR, f"profiles_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 输出统计
    print("\n" + "=" * 50)
    print(f"采集完成！成功 {len(results)}/{len(pids)}")
    print(f"结果保存到: {output_path}")
    for r in results:
        print(f"  {r.get('display_name', '?'):15s} fans={r.get('fans_count', 0):6d} posts={r.get('post_count', 0):3d}  {r.get('xhs_id', '')}")


def main():
    parser = argparse.ArgumentParser(description="高效采集小红书 profile")
    parser.add_argument("--limit", type=int, default=20, help="采集数量（默认 20）")
    parser.add_argument("--urls", type=str, default=None, help="从文件读取 URL")
    parser.add_argument("--headless", action="store_true", help="无界面模式（默认有界面，方便处理验证码）")
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, urls_file=args.urls, headed=not args.headless))


if __name__ == "__main__":
    main()
