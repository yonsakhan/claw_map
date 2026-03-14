import asyncio
import random
import logging
import os
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Page, BrowserContext
from fake_useragent import UserAgent
from src.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("XiaohongshuScraper")

class XiaohongshuScraper:
    def __init__(
        self,
        headless: bool = True,
        storage_state_path: str = "src/storage/xhs_state.json",
        max_fetch_retries: int = 2,
        retry_backoff_seconds: float = 2.0,
        cookie_string: Optional[str] = None,
    ):
        self.headless = headless
        self.ua = UserAgent()
        self.storage_state_path = storage_state_path
        self.max_fetch_retries = max_fetch_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.cookie_string = self._normalize_cookie_string(cookie_string or settings.xhs_cookie)

    async def _random_sleep(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """模拟人类操作的随机等待时间。"""
        sleep_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Sleeping for {sleep_time:.2f} seconds...")
        await asyncio.sleep(sleep_time)

    async def _get_random_user_agent(self) -> str:
        """获取随机 User-Agent。"""
        try:
            return self.ua.random
        except Exception:
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _normalize_url(self, url: str) -> str:
        return (url or "").strip().strip("`").strip("'").strip('"')

    def _normalize_cookie_string(self, cookie_string: Optional[str]) -> str:
        return (cookie_string or "").strip().strip("`").strip("'").strip('"')

    def _normalize_whitespace(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    def _has_cookie_string(self) -> bool:
        return bool(self.cookie_string)

    def _build_playwright_cookies(self, cookie_string: str) -> List[Dict[str, Any]]:
        payload = cookie_string.strip()
        if payload.startswith("["):
            try:
                entries = json.loads(payload)
                cookies: List[Dict[str, Any]] = []
                for item in entries:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    value = str(item.get("value") or "").strip()
                    if not name:
                        continue
                    cookie: Dict[str, Any] = {
                        "name": name,
                        "value": value,
                        "path": item.get("path") or "/",
                        "domain": item.get("domain") or ".xiaohongshu.com",
                        "httpOnly": bool(item.get("httpOnly", False)),
                        "secure": bool(item.get("secure", True)),
                    }
                    expires = item.get("expirationDate")
                    if expires is not None:
                        try:
                            cookie["expires"] = float(expires)
                        except (TypeError, ValueError):
                            pass
                    same_site = str(item.get("sameSite") or "").lower()
                    if same_site == "lax":
                        cookie["sameSite"] = "Lax"
                    elif same_site == "strict":
                        cookie["sameSite"] = "Strict"
                    elif same_site == "none":
                        cookie["sameSite"] = "None"
                    cookies.append(cookie)
                return cookies
            except json.JSONDecodeError:
                logger.warning("Cookie JSON 解析失败，回退到 key=value 解析模式。")
        pairs = [part.strip() for part in cookie_string.split(";") if part.strip()]
        cookies: List[Dict[str, Any]] = []
        for pair in pairs:
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                }
            )
        return cookies

    async def _apply_cookie_login(self, context: BrowserContext):
        if not self._has_cookie_string():
            return
        cookies = self._build_playwright_cookies(self.cookie_string)
        if not cookies:
            logger.warning("Cookie 字符串格式无效，跳过 Cookie 注入。")
            return
        await context.add_cookies(cookies)
        logger.info(f"已注入 Cookie 数量: {len(cookies)}")

    def _can_use_storage_state(self) -> bool:
        return os.path.exists(self.storage_state_path)

    def _invalidate_storage_state(self):
        if self._can_use_storage_state():
            try:
                os.remove(self.storage_state_path)
                logger.warning(f"检测到状态失效，已移除本地状态文件: {self.storage_state_path}")
            except Exception as exc:
                logger.warning(f"移除状态文件失败: {exc}")

    async def _persist_storage_state(self, context: BrowserContext):
        try:
            os.makedirs(os.path.dirname(self.storage_state_path), exist_ok=True)
            await context.storage_state(path=self.storage_state_path)
            logger.info(f"已刷新登录状态: {self.storage_state_path}")
        except Exception as exc:
            logger.warning(f"刷新登录状态失败: {exc}")

    async def login_and_save_state(self):
        """
        手动登录并保存状态到本地文件。
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # 本地运行必须开启界面用于扫码
            context = await browser.new_context(
                user_agent=await self._get_random_user_agent(),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            logger.info("正在打开小红书首页...")
            login_url = self._normalize_url("https://www.xiaohongshu.com/explore")
            await page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
            
            print("\n" + "="*50)
            print("🚀 请在弹出的浏览器窗口中完成小红书登录（扫码等）。")
            print("👉 确认登录成功并进入主页后，请回到这里按下【回车键】确认保存状态。")
            print("="*50 + "\n")
            
            # 使用 aioconsole 或简单的同步 input（在 asyncio 中建议用这种方式处理手动交互）
            await asyncio.get_event_loop().run_in_executor(None, input, "等待登录完成后按回车...")
            
            try:
                logger.info("正在捕捉登录状态并持久化...")
                # 额外等待 2 秒确保 Cookie 同步完毕
                await asyncio.sleep(2)
                
                # 确保目录存在
                os.makedirs(os.path.dirname(self.storage_state_path), exist_ok=True)
                
                await context.storage_state(path=self.storage_state_path)
                logger.info(f"✅ 状态已成功保存至: {self.storage_state_path}")
            except Exception as e:
                logger.error(f"保存状态失败: {e}")
            finally:
                await browser.close()

    async def login_with_cookie_and_save_state(self, cookie_string: Optional[str] = None) -> bool:
        candidate = self._normalize_cookie_string(cookie_string or self.cookie_string)
        if not candidate:
            logger.warning("未提供 Cookie 字符串，无法进行 Cookie 登录。")
            return False
        self.cookie_string = candidate
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent=await self._get_random_user_agent(),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            try:
                await self._apply_cookie_login(context)
                login_url = self._normalize_url("https://www.xiaohongshu.com/explore")
                await page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
                await self._random_sleep(2, 4)
                blocked = await self._check_login_block(page)
                if blocked:
                    logger.warning("Cookie 登录未通过，页面仍显示登录拦截。")
                    return False
                await self._persist_storage_state(context)
                logger.info("✅ Cookie 登录成功并已保存状态。")
                return True
            except Exception as exc:
                logger.warning(f"Cookie 登录异常: {exc}")
                return False
            finally:
                await browser.close()

    async def _check_login_block(self, page: Page) -> bool:
        """检查是否遇到登录阻塞。"""
        try:
            if "login" in page.url:
                return True
            
            login_selectors = [".login-container", ".login-modal", "text=登录"]
            for selector in login_selectors:
                if await page.locator(selector).first.is_visible(timeout=500):
                    return True
            body_text = await page.locator("body").inner_text()
            block_keywords = [
                "马上登录即可",
                "登录后推荐更懂你的笔记",
                "手机号登录",
                "扫码",
                "获取验证码",
            ]
            if any(keyword in body_text for keyword in block_keywords):
                return True
            return False
        except Exception:
            return False

    def _should_retry_fetch(self, attempt: int, blocked: bool, has_error: bool) -> bool:
        if attempt >= self.max_fetch_retries:
            return False
        return blocked or has_error

    def _parse_profile_text(self, raw_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
        joined = "\n".join(lines)
        account_no_match = re.search(r"小红书号[:：]\s*([0-9A-Za-z_-]+?)(?=IP属地|\s|$)", joined)
        ip_match = re.search(r"IP属地[:：]\s*([^\n\r]+)", joined)
        follow_match = re.search(r"(\d+)\s*关注", joined)
        fans_match = re.search(r"(\d+)\s*粉丝", joined)
        likes_match = re.search(r"(\d+)\s*获赞与收藏", joined)
        tabs = [tab for tab in ["关注", "笔记", "收藏"] if re.search(rf"(^|\s){tab}($|\s)", joined)]
        display_name = ""
        for line in lines:
            if "小红书号" in line:
                break
            if line not in {"关注", "笔记", "收藏"}:
                display_name = line
                break
        account_line_idx = next((idx for idx, line in enumerate(lines) if "小红书号" in line), -1)
        stats_start_idx = next(
            (
                idx
                for idx, line in enumerate(lines)
                if re.match(r"^\d+\s*(关注|粉丝|获赞与收藏)$", line)
            ),
            len(lines),
        )
        bio_candidates = []
        if account_line_idx >= 0 and stats_start_idx > account_line_idx + 1:
            bio_candidates = lines[account_line_idx + 1 : stats_start_idx]
        elif len(lines) > 1:
            bio_candidates = lines[1:stats_start_idx]
        bio = " ".join([line for line in bio_candidates if line not in {"关注", "笔记", "收藏"}][:3]).strip()
        location = ""
        if ip_match:
            location = self._normalize_whitespace(ip_match.group(1))
        if not location:
            for line in bio_candidates:
                if any(token in line for token in ["北京", "上海", "广州", "深圳", "广东", "江苏", "浙江", "四川", "重庆"]):
                    location = line
                    break
        return {
            "display_name": display_name,
            "account_no": account_no_match.group(1) if account_no_match else "",
            "ip_location": self._normalize_whitespace(ip_match.group(1)) if ip_match else "",
            "bio": bio,
            "location": location,
            "follow_count": int(follow_match.group(1)) if follow_match else 0,
            "fans_count": int(fans_match.group(1)) if fans_match else 0,
            "likes_favorites_count": int(likes_match.group(1)) if likes_match else 0,
            "tabs": tabs,
        }

    async def _extract_account_profile(self, page: Page, account_url: str, fallback_display_name: str = "") -> Dict[str, Any]:
        body_text = await page.locator("body").inner_text()
        parsed = self._parse_profile_text(body_text)
        resolved_url = self._normalize_url(account_url or page.url)
        profile_id = parsed.get("account_no") or self._extract_account_id_from_url(resolved_url)
        display_name = parsed.get("display_name") or fallback_display_name
        profile: Dict[str, Any] = {
            "id": str(profile_id or ""),
            "display_name": display_name,
            "profile_url": resolved_url,
            "bio": parsed.get("bio", ""),
            "location": parsed.get("location") or parsed.get("ip_location") or "",
            "ip_location": parsed.get("ip_location", ""),
            "xhs_id": parsed.get("account_no", ""),
            "stats": {
                "follow_count": parsed.get("follow_count", 0),
                "fans_count": parsed.get("fans_count", 0),
                "likes_favorites_count": parsed.get("likes_favorites_count", 0),
            },
            "tabs": parsed.get("tabs", []),
        }
        return profile

    async def _collect_account_candidates_from_explore(self, page: Page, limit: int = 10) -> List[Tuple[str, str]]:
        selectors = ["span.name", "[class*='name']"]
        candidates: List[Tuple[str, str]] = []
        seen = set()
        for selector in selectors:
            nodes = await page.locator(selector).all()
            for node in nodes:
                if len(candidates) >= limit:
                    break
                try:
                    name = self._normalize_whitespace(await node.inner_text())
                    if not name:
                        continue
                    href = await node.evaluate(
                        """(el) => {
                            const anchor = el.closest('a') || el.querySelector('a');
                            return anchor ? anchor.getAttribute('href') : null;
                        }"""
                    )
                    if not href:
                        continue
                    url = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
                    key = (name, url)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(key)
                except Exception:
                    continue
            if candidates:
                break
        return candidates[:limit]

    async def collect_accounts_from_explore(self, limit: int = 5) -> List[Dict[str, Any]]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            use_state = self._can_use_storage_state()
            storage_state = self.storage_state_path if use_state else None
            context = await browser.new_context(
                storage_state=storage_state,
                user_agent=await self._get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            if not use_state and self._has_cookie_string():
                await self._apply_cookie_login(context)
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await context.new_page()
            try:
                await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=60000)
                await self._random_sleep(2, 3)
                if await self._check_login_block(page):
                    return []
                candidates = await self._collect_account_candidates_from_explore(page, limit=limit)
                results: List[Dict[str, Any]] = []
                for name, url in candidates:
                    profile_payload = await self.fetch_account_dimensions(url)
                    if not profile_payload:
                        continue
                    profile_payload["seed_name"] = name
                    results.append(profile_payload)
                return results
            finally:
                await browser.close()

    async def fetch_profile(self, url: str) -> Optional[Dict[str, Any]]:
        """获取小红书用户主页信息。"""
        async with async_playwright() as p:
            normalized_url = self._normalize_url(url)
            for attempt in range(self.max_fetch_retries + 1):
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=['--disable-blink-features=AutomationControlled']
                )
                use_state = self._can_use_storage_state()
                storage_state = self.storage_state_path if use_state else None
                if use_state:
                    logger.info(f"使用保存的登录状态: {self.storage_state_path}")

                context = await browser.new_context(
                    storage_state=storage_state,
                    user_agent=await self._get_random_user_agent(),
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN'
                )
                if not use_state and self._has_cookie_string():
                    await self._apply_cookie_login(context)
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = await context.new_page()
                blocked = False
                has_error = False
                try:
                    logger.info(f"正在访问主页: {normalized_url}")
                    await page.goto(normalized_url, wait_until="domcontentloaded", timeout=60000)
                    await self._random_sleep(3, 5)
                    blocked = await self._check_login_block(page)
                    if blocked:
                        logger.warning("检测到登录拦截。")
                        if use_state:
                            self._invalidate_storage_state()
                    else:
                        title = await page.title()
                        profile = await self._extract_account_profile(page, normalized_url, fallback_display_name=title)
                        posts = await self.scroll_and_fetch_posts(page, limit=10)
                        if (
                            not posts
                            and title == "小红书 - 你的生活兴趣社区"
                            and not profile.get("xhs_id")
                            and not profile.get("display_name")
                        ):
                            blocked = True
                            logger.warning("页面返回通用标题且无帖子，疑似仍处于登录拦截。")
                            if use_state:
                                self._invalidate_storage_state()
                        else:
                            if use_state:
                                await self._persist_storage_state(context)
                            return {"url": normalized_url, "title": title, "posts": posts, "profile": profile}
                except Exception as e:
                    has_error = True
                    logger.error(f"抓取失败: {e}")
                finally:
                    await browser.close()
                if not self._should_retry_fetch(attempt, blocked, has_error):
                    break
                wait_seconds = self.retry_backoff_seconds * (attempt + 1)
                logger.info(f"准备重试抓取，第 {attempt + 1} 次重试，等待 {wait_seconds:.1f} 秒")
                await asyncio.sleep(wait_seconds)
            logger.warning("多次抓取后仍失败，请重新运行 local_login.py 更新登录状态。")
            return None

    async def fetch_account_dimensions(self, account_url: str, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        payload = await self.fetch_profile(account_url)
        if not payload:
            return None
        payload_profile = payload.get("profile", {}) or {}
        resolved_account_id = account_id or payload_profile.get("id") or self._extract_account_id_from_url(account_url)
        profile = {
            "id": resolved_account_id,
            "display_name": payload_profile.get("display_name") or payload.get("title", ""),
            "profile_url": payload_profile.get("profile_url") or account_url,
            "bio": payload_profile.get("bio", ""),
            "location": payload_profile.get("location", ""),
            "ip_location": payload_profile.get("ip_location", ""),
            "xhs_id": payload_profile.get("xhs_id", ""),
            "stats": payload_profile.get("stats", {}),
            "tabs": payload_profile.get("tabs", []),
        }
        return {
            "account_id": resolved_account_id,
            "profile": profile,
            "posts": payload.get("posts", []),
            "likes": [],
            "favorites": [],
            "follows": [],
        }

    async def scroll_and_fetch_posts(self, page: Page, limit: int = 10) -> List[Dict[str, Any]]:
        """滚动并解析帖子。"""
        posts = []
        note_selectors = [".note-item", "section.note-item", "[class*='note-item']"]
        prev_height = 0
        
        while len(posts) < limit:
            if await self._check_login_block(page): break
            
            elements = []
            for note_selector in note_selectors:
                elements = await page.locator(note_selector).all()
                if elements:
                    break
            for el in elements:
                if len(posts) >= limit: break
                try:
                    title_el = el.locator(".title, [class*='title']")
                    link_el = el.locator("a.cover, a[href*='/explore/']")
                    title = await title_el.inner_text() if await title_el.count() > 0 else ""
                    link = await link_el.get_attribute("href") if await link_el.count() > 0 else ""
                    post_id = link.split("/")[-1] if link else f"tmp_{len(posts)}"
                    
                    if not any(p['id'] == post_id for p in posts):
                        posts.append({"id": post_id, "title": title, "url": f"https://www.xiaohongshu.com{link}"})
                        logger.info(f"发现帖子: {title[:15]}...")
                except: continue

            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await self._random_sleep(2, 4)
            
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == prev_height: break
            prev_height = new_height
            
        return posts[:limit]

    def _extract_account_id_from_url(self, account_url: str) -> str:
        parsed = urlparse(account_url)
        path = parsed.path.strip("/")
        if not path:
            return ""
        return path.split("/")[-1]

if __name__ == "__main__":
    # 示例用法
    async def main():
        scraper = XiaohongshuScraper(headless=True)
        # 如果是第一次在本地运行，请取消下面这行的注释来扫码登录：
        # await scraper.login_and_save_state()
        await scraper.fetch_profile("https://www.xiaohongshu.com/user/profile/5b15392b4260905102559902")
    asyncio.run(main())
