import asyncio
import random
import logging
import os
import json
import re
import time
import html
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
from urllib.parse import urlparse
from urllib.parse import parse_qs
from playwright.async_api import async_playwright, Page, BrowserContext, Browser
from playwright_stealth import Stealth
from fake_useragent import UserAgent
from src.config import settings
from src.crawler.proxy_manager import ProxyManager
from src.crawler.errors import LoginRequiredError, RateLimitedError
from src.storage.crawl_runtime_store import CrawlRuntimeStore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("XiaohongshuScraper")

DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}
DETAIL_VIEWPORT = {"width": 1280, "height": 800}
STEALTH_INIT_SCRIPT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"

class XiaohongshuScraper:
    def __init__(
        self,
        headless: bool = True,
        storage_state_path: str = "src/storage/xhs_state.json",
        max_fetch_retries: int = 2,
        retry_backoff_seconds: float = 2.0,
        cookie_string: Optional[str] = None,
        force_desktop_ua: bool = True,
    ):
        self.headless = headless
        self.ua = UserAgent()
        self.storage_state_path = storage_state_path
        self.max_fetch_retries = max_fetch_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        cookie_source = settings.xhs_cookie if cookie_string is None else cookie_string
        self.cookie_string = self._normalize_cookie_string(cookie_source)
        self.proxy_manager = ProxyManager()
        self.runtime_store: Optional[CrawlRuntimeStore] = None
        self.force_desktop_ua = bool(force_desktop_ua)
        # 礼貌策略：降低触发频控/风控概率（不是绕过风控）
        self._last_request_at: float = 0.0
        self._cooldown_until: float = 0.0
        self.min_delay_seconds: float = float(getattr(settings, "xhs_min_delay_seconds", 8))
        self.max_delay_seconds: float = float(getattr(settings, "xhs_max_delay_seconds", 15))
        self.rate_limit_cooldown_seconds: int = int(getattr(settings, "xhs_rate_limit_cooldown_seconds", 1800))

    async def _random_sleep(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """模拟人类操作的随机等待时间。"""
        sleep_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Sleeping for {sleep_time:.2f} seconds...")
        await asyncio.sleep(sleep_time)

    def _get_runtime_store(self) -> CrawlRuntimeStore:
        if self.runtime_store is None:
            self.runtime_store = CrawlRuntimeStore()
        return self.runtime_store

    def _ensure_storage_parent_dir(self) -> str:
        parent_dir = os.path.dirname(self.storage_state_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        return parent_dir

    async def _before_navigation(self):
        """在关键页面跳转前做节流/冷却，避免高频触发平台风控。"""
        now = time.monotonic()
        if self._cooldown_until and now < self._cooldown_until:
            wait_s = max(0.0, self._cooldown_until - now)
            logger.warning(f"触发冷却窗口，暂停 {wait_s:.0f}s 后再继续。")
            await asyncio.sleep(wait_s)
            now = time.monotonic()
        shared_cooldown_until = self._get_runtime_store().get_rate_limit_cooldown_until_epoch()
        if shared_cooldown_until:
            shared_wait_s = max(0.0, float(shared_cooldown_until) - time.time())
            if shared_wait_s > 0:
                logger.warning(f"检测到共享冷却窗口，暂停 {shared_wait_s:.0f}s 后再继续。")
                await asyncio.sleep(shared_wait_s)
                now = time.monotonic()

        # 把“随机间隔”当作目标请求间隔，避免先补最小值再额外 sleep 一次。
        target_gap = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        elapsed = (now - self._last_request_at) if self._last_request_at else 0.0
        wait_s = max(0.0, target_gap - elapsed)
        if wait_s > 0:
            await asyncio.sleep(wait_s)
        self._last_request_at = time.monotonic()

    def _enter_rate_limit_cooldown(self, reason: str = ""):
        # 进入较长冷却窗口，避免继续触发警告/封禁
        self._cooldown_until = time.monotonic() + float(self.rate_limit_cooldown_seconds)
        self._get_runtime_store().set_rate_limit_cooldown(
            seconds=self.rate_limit_cooldown_seconds,
            reason=reason,
            source=f"pid:{os.getpid()}",
        )
        logger.warning(f"检测到访问频繁/风控，进入冷却窗口 {self.rate_limit_cooldown_seconds}s。{reason}")

    async def _launch_browser(self, playwright):
        proxy_server = await self.proxy_manager.get_random_proxy()
        launch_kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        }
        if proxy_server:
            launch_kwargs["proxy"] = {"server": proxy_server}
            logger.info(f"使用代理: {proxy_server}")
        return await playwright.chromium.launch(**launch_kwargs)

    async def _create_scraper_page(
        self,
        browser: Browser,
        *,
        viewport: Dict[str, int],
    ) -> Tuple[BrowserContext, Page, bool]:
        use_state = self._can_use_storage_state()
        storage_state = self.storage_state_path if use_state else None
        if use_state:
            logger.info(f"使用保存的登录状态: {self.storage_state_path}")
        context = await browser.new_context(
            storage_state=storage_state,
            user_agent=await self._get_random_user_agent(),
            viewport=dict(viewport),
            locale="zh-CN",
        )
        if not use_state and self._has_cookie_string():
            await self._apply_cookie_login(context)
        await context.add_init_script(STEALTH_INIT_SCRIPT)
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        return context, page, use_state

    async def _run_with_scraper_session(
        self,
        playwright,
        action: Callable[[Page, BrowserContext, bool], Awaitable[Any]],
        *,
        viewport: Dict[str, int],
    ) -> Any:
        browser = await self._launch_browser(playwright)
        try:
            context, page, use_state = await self._create_scraper_page(browser, viewport=viewport)
            return await action(page, context, use_state)
        finally:
            await browser.close()

    async def _get_random_user_agent(self) -> str:
        """获取随机 User-Agent。"""
        # 小红书会根据 UA/视口做适配；如果 UA 被识别为 Mobile，网页就会“像手机版”。
        # 因此默认强制使用桌面 UA，避免每次打开都是移动端布局。
        if self.force_desktop_ua:
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        try:
            ua = self.ua.random
            # 尽量过滤掉移动端 UA（防止误判为手机版）
            for _ in range(5):
                if any(token in ua for token in ["Mobile", "Android", "iPhone", "iPad"]):
                    ua = self.ua.random
                    continue
                break
            return ua
        except Exception:
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def ensure_logged_in(self) -> bool:
        """进入站点后先判断是否已登录；如未登录则在浏览器里等待用户完成登录并保存状态。

        说明：
        - 只适用于 headless=False（需要弹出浏览器让你操作）
        - headless=True 时只做远端校验，不会触发交互式登录
        """
        if self.headless:
            if not self._can_use_storage_state() and not self._has_cookie_string():
                return False
            async with async_playwright() as p:
                browser = await self._launch_browser(p)
                try:
                    use_state = self._can_use_storage_state()
                    storage_state = self.storage_state_path if use_state else None
                    context = await browser.new_context(
                        storage_state=storage_state,
                        user_agent=await self._get_random_user_agent(),
                        viewport={"width": 1280, "height": 800},
                        locale="zh-CN",
                    )
                    if not use_state and self._has_cookie_string():
                        await self._apply_cookie_login(context)
                    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    page = await context.new_page()
                    await self._before_navigation()
                    await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=120000)
                    await self._random_sleep(2, 3)
                    blocked, reason = await self._get_login_block_reason(page)
                    if blocked:
                        if use_state:
                            self._invalidate_storage_state()
                        logger.warning(f"headless 登录态校验失败: {reason}")
                        return False
                    await self._persist_storage_state(context)
                    return True
                except Exception as exc:
                    logger.warning(f"headless 登录态校验失败: {exc}")
                    return False
                finally:
                    await browser.close()

        async with async_playwright() as p:
            browser = await self._launch_browser(p)
            try:
                use_state = self._can_use_storage_state()
                storage_state = self.storage_state_path if use_state else None
                context = await browser.new_context(
                    storage_state=storage_state,
                    user_agent=await self._get_random_user_agent(),
                    viewport={"width": 1280, "height": 800},
                    locale="zh-CN",
                )
                if not use_state and self._has_cookie_string():
                    await self._apply_cookie_login(context)
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = await context.new_page()
                await self._before_navigation()
                await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=120000)
                await self._random_sleep(2, 3)
                blocked, reason = await self._get_login_block_reason(page)
                if not blocked:
                    # 已登录（或至少不处于登录拦截）
                    await self._persist_storage_state(context)
                    return True
            finally:
                await browser.close()

        # 走到这里说明被登录拦截：进入交互式登录流程（会循环检测到登录成功才保存）
        await self.login_and_save_state()
        return True

    def _normalize_url(self, url: str) -> str:
        # 兼容用户在命令行里把 URL 写成 `...`、'...'、"..." 或全角 `｀...｀`
        return (url or "").strip().strip("`").strip("´").strip("｀").strip("'").strip('"').strip()

    def _normalize_cookie_string(self, cookie_string: Optional[str]) -> str:
        return (cookie_string or "").strip().strip("`").strip("´").strip("｀").strip("'").strip('"').strip()

    def _normalize_whitespace(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())

    def _is_display_name_candidate(self, text: str) -> bool:
        """判断 text 是否可能是用户昵称（过滤 footer/导航/风控提示等噪音）。"""
        value = self._normalize_whitespace(text or "")
        if not value:
            return False
        if value in {"关注", "笔记", "收藏"}:
            return False
        # footer / 导航常见噪音
        noise_exact = {
            "创作中心",
            "业务合作",
            "更多",
            "发现",
            "直播",
            "发布",
            "通知",
            "我",
            "搜索小红书",
            "© 2014-2026",
            "行吟信息科技（上海）有限公司",
        }
        if value in noise_exact:
            return False
        if value.startswith("©") or "ICP备" in value or "公网安备" in value:
            return False
        if "行吟信息科技" in value or "有限公司" in value or "用户协议" in value or "隐私" in value:
            return False
        # 昵称一般不会包含 IP 属地提示
        if "IP属地" in value:
            return False
        # 长度限制（过长通常是 bio/广告）
        return 2 <= len(value) <= 30

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
            self._ensure_storage_parent_dir()
            await context.storage_state(path=self.storage_state_path)
            logger.info(f"已刷新登录状态: {self.storage_state_path}")
        except Exception as exc:
            logger.warning(f"刷新登录状态失败: {exc}")

    def _raise_login_block(
        self,
        *,
        scene: str,
        reason: str = "",
        use_state: bool = False,
    ) -> None:
        detail = self._normalize_whitespace(reason)
        if detail:
            logger.warning(f"{scene} 检测到登录拦截：{detail}")
        else:
            logger.warning(f"{scene} 检测到登录拦截。")
        # 仅对频控错误触发冷却，不删除状态文件
        if "300013" in detail or "访问频繁" in detail:
            self._enter_rate_limit_cooldown(detail)
            raise RateLimitedError(f"rate limited: {detail}")
        suffix = f"{scene}: {detail}" if detail else scene
        raise LoginRequiredError(f"login blocked: {suffix}")

    async def _ensure_not_login_blocked(self, page: Page, *, scene: str, use_state: bool = False) -> None:
        blocked, reason = await self._get_login_block_reason(page)
        if not blocked:
            return
        # 验证码页面（扫码验证）：headed 模式下等待用户扫码
        if "captcha" in page.url and not self.headless:
            logger.info("检测到扫码验证码，等待用户扫码验证（最多 90s）...")
            for i in range(90):
                await asyncio.sleep(1)
                if "captcha" not in page.url and "login" not in page.url:
                    logger.info("扫码验证通过（耗时 %ds）", i + 1)
                    await self._persist_storage_state(page.context)
                    return
                if i > 0 and i % 15 == 0:
                    logger.info("仍在等待扫码... (%ds)", i)
            logger.warning("扫码验证超时")
        self._raise_login_block(scene=scene, reason=reason, use_state=use_state)

    async def _open_page(
        self,
        page: Page,
        url: str,
        *,
        scene: str,
        use_state: bool = False,
        timeout: int = 60000,
        wait_until: str = "domcontentloaded",
        sleep_range: Tuple[float, float] = (2, 3),
        wait_for_networkidle: bool = False,
        networkidle_timeout: int = 60000,
    ) -> str:
        normalized_url = self._normalize_url(url)
        await self._before_navigation()
        await page.goto(normalized_url, wait_until=wait_until, timeout=timeout)
        if wait_for_networkidle:
            try:
                await page.wait_for_load_state("networkidle", timeout=networkidle_timeout)
            except Exception:
                pass
        min_sleep, max_sleep = sleep_range
        if max_sleep > 0:
            await self._random_sleep(min_sleep, max_sleep)
        await self._ensure_not_login_blocked(page, scene=scene, use_state=use_state)
        return normalized_url

    async def login_and_save_state(self):
        """
        手动登录并保存状态到本地文件。
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # 手动登录建议关闭代理以避免扫码异常
            context = await browser.new_context(
                user_agent=await self._get_random_user_agent(),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            logger.info("正在打开小红书首页...")
            login_url = self._normalize_url("https://www.xiaohongshu.com/explore")
            await self._before_navigation()
            await page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
            
            print("\n" + "="*50)
            print("请在弹出的浏览器窗口中完成小红书登录（扫码/验证码等）。")
            print("登录完成后回到终端按【回车】；程序会检测是否仍被登录页拦截，只有确认登录成功才会保存状态。")
            print("="*50 + "\n")
            
            try:
                # 允许多次尝试，避免“按回车时其实还没登录成功”
                for _ in range(5):
                    await asyncio.get_event_loop().run_in_executor(None, input, "等待登录完成后按回车...")
                    await asyncio.sleep(2)

                    blocked, reason = await self._get_login_block_reason(page)
                    if blocked:
                        logger.warning(f"仍检测到登录拦截（{reason}）。请继续在浏览器里完成登录后再按回车。")
                        continue

                    logger.info("检测到已通过登录拦截，开始保存登录状态...")
                    await self._persist_storage_state(context)

                    # 额外把 Cookie 导出为 JSON（便于你需要时放到 .env 的 XHS_COOKIE）
                    try:
                        cookies = await context.cookies("https://www.xiaohongshu.com")
                        parent_dir = self._ensure_storage_parent_dir()
                        cookie_path = os.path.join(parent_dir or ".", "xhs_cookies.json")
                        with open(cookie_path, "w", encoding="utf-8") as f:
                            json.dump(cookies, f, ensure_ascii=False, indent=2)
                        logger.info(f"已导出 Cookie: {cookie_path}（{len(cookies)} 条）")
                    except Exception as exc:
                        logger.warning(f"导出 Cookie 失败（不影响状态保存）: {exc}")

                    logger.info("✅ 手动登录成功并已保存状态。")
                    return

                raise RuntimeError("多次确认后仍处于登录拦截状态，请检查是否确实登录成功/是否触发风控。")
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
                await self._before_navigation()
                await page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
                await self._random_sleep(2, 4)
                blocked = await self._check_login_block(page)
                if blocked:
                    logger.warning("Cookie 登录未通过，页面仍显示登录拦截。")
                    return False
                await self._persist_storage_state(context)
                try:
                    cookies = await context.cookies("https://www.xiaohongshu.com")
                    parent_dir = self._ensure_storage_parent_dir()
                    cookie_path = os.path.join(parent_dir or ".", "xhs_cookies.json")
                    with open(cookie_path, "w", encoding="utf-8") as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                    logger.info(f"已导出 Cookie: {cookie_path}（{len(cookies)} 条）")
                except Exception as exc:
                    logger.warning(f"导出 Cookie 失败（不影响状态保存）: {exc}")
                logger.info("✅ Cookie 登录成功并已保存状态。")
                return True
            except Exception as exc:
                logger.warning(f"Cookie 登录异常: {exc}")
                return False
            finally:
                await browser.close()

    async def _check_login_block(self, page: Page) -> bool:
        """检查是否遇到登录阻塞。"""
        blocked, _reason = await self._get_login_block_reason(page)
        return blocked

    async def _get_login_block_reason(self, page: Page) -> tuple[bool, str]:
        """返回 (是否被登录拦截, 原因简述)。"""
        try:
            # 1) 显式跳转登录页 / 风控错误页
            if "website-login/error" in page.url:
                # 例如：.../website-login/error?error_code=300013&error_msg=访问频繁...
                qs = parse_qs(urlparse(page.url).query or "")
                err_code = (qs.get("error_code") or [""])[0]
                err_msg = (qs.get("error_msg") or [""])[0]
                if err_code or err_msg:
                    return True, f"website_login_error: {err_code} {err_msg}".strip()
                return True, f"url_contains_login: {page.url}"
            if "login" in page.url:
                return True, f"url_contains_login: {page.url}"
            
            login_selectors = [".login-container", ".login-modal", "text=登录"]
            for selector in login_selectors:
                if await page.locator(selector).first.is_visible(timeout=500):
                    return True, f"selector_visible: {selector}"
            body_text = await page.locator("body").inner_text()
            block_keywords = [
                "马上登录即可",
                "登录后推荐更懂你的笔记",
                "手机号登录",
                "扫码",
                "获取验证码",
            ]
            if any(keyword in body_text for keyword in block_keywords):
                hit = next((kw for kw in block_keywords if kw in body_text), "keyword_hit")
                return True, f"keyword_hit: {hit}"
            return False, ""
        except Exception:
            return False, ""

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
        note_count_match = re.search(r"笔记[・·\s]*([0-9]+)", joined)
        tabs = [tab for tab in ["关注", "笔记", "收藏"] if re.search(rf"(^|\s){tab}($|\s)", joined)]
        # display_name：尽量从“小红书号”之前的区域提取，但要过滤掉 UI 噪音词
        ui_noise = {
            "创作中心",
            "业务合作",
            "更多",
            "发现",
            "直播",
            "发布",
            "通知",
            "我",
            "搜索小红书",
            "© 2014-2026",
            "行吟信息科技（上海）有限公司",  # 小红书公司名，常出现在页面底部
            "行吟信息科技",
            "小红书",
        }
        display_name = ""
        account_line_idx = next((idx for idx, line in enumerate(lines) if "小红书号" in line), -1)
        name_candidates = lines[: account_line_idx if account_line_idx > 0 else min(len(lines), 30)]
        for line in name_candidates:
            if line in {"关注", "笔记", "收藏"}:
                continue
            if line in ui_noise:
                continue
            # 过滤 copyright/footer
            if line.startswith("©") or re.search(r"\b20\d{2}\b", line):
                continue
            if "IP属地" in line:
                continue
            if "小红书号" in line:
                continue
            # 过滤公司/组织名称（包含"公司"、"科技"、"有限"等）
            if any(kw in line for kw in ["公司", "科技", "有限", "集团", "股份"]):
                continue
            # 过长/过短的通常不是昵称
            if not (2 <= len(line) <= 30):
                continue
            display_name = line
            break
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
            "note_count": int(note_count_match.group(1)) if note_count_match else 0,
            "tabs": tabs,
        }

    async def _extract_account_profile(self, page: Page, account_url: str, fallback_display_name: str = "") -> Dict[str, Any]:
        # 先尝试从 DOM 里直接取昵称（比 body 文本更稳，不容易误把“公司名/版权”当昵称）
        dom_display_name = ""
        for selector in [
            # 下面是一些“尽量通用”的候选，实际命中哪个取决于小红书页面版本
            "[class*='user'] [class*='name']",
            "[class*='user-name']",
            "[class*='nickname']",
            "h1",
            "header [class*='name']",
        ]:
            try:
                loc = page.locator(selector).first
                if await loc.count() <= 0:
                    continue
                txt = self._normalize_whitespace(await loc.inner_text())
                if self._is_display_name_candidate(txt):
                    dom_display_name = txt
                    break
            except Exception:
                continue

        body_text = await page.locator("body").inner_text()
        parsed = self._parse_profile_text(body_text)
        resolved_url = self._normalize_url(account_url or page.url)
        profile_id = parsed.get("account_no") or self._extract_account_id_from_url(resolved_url)
        # fallback_display_name 可能会拿到 footer（例如“行吟信息科技（上海）有限公司”），因此也要过滤
        display_name = dom_display_name or parsed.get("display_name") or fallback_display_name
        if not self._is_display_name_candidate(display_name):
            display_name = ""
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
                "note_count": parsed.get("note_count", 0),
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
            async def action(page: Page, _context: BrowserContext, use_state: bool) -> List[Dict[str, Any]]:
                await self._open_page(
                    page,
                    "https://www.xiaohongshu.com/explore",
                    scene="explore",
                    use_state=use_state,
                )
                candidates = await self._collect_account_candidates_from_explore(page, limit=limit)
                results: List[Dict[str, Any]] = []
                for name, url in candidates:
                    profile_payload = await self.fetch_account_dimensions(url)
                    if not profile_payload:
                        continue
                    profile_payload["seed_name"] = name
                    results.append(profile_payload)
                return results

            return await self._run_with_scraper_session(p, action, viewport=DEFAULT_VIEWPORT)

    async def collect_accounts_from_search(self, search_url: str, limit: int = 200) -> List[str]:
        async with async_playwright() as p:
            async def action(page: Page, _context: BrowserContext, use_state: bool) -> List[str]:
                await self._open_page(
                    page,
                    search_url,
                    scene="search",
                    use_state=use_state,
                )
                await self._click_search_user_tab(page)
                urls = await self._scroll_collect_profile_urls(page, limit=limit)
                if not urls:
                    # 采不到用户链接时，通常是“没有切到用户 tab / 页面结构变化 / 搜索结果为空”
                    try:
                        title = await page.title()
                    except Exception:
                        title = ""
                    logger.warning(f"未从搜索页提取到用户链接。title={title} url={page.url}")
                return urls

            return await self._run_with_scraper_session(p, action, viewport=DEFAULT_VIEWPORT)

    async def fetch_collections(self, profile_url: str) -> Dict[str, Any]:
        async with async_playwright() as p:
            async def action(page: Page, _context: BrowserContext, use_state: bool) -> Dict[str, Any]:
                await self._open_page(
                    page,
                    profile_url,
                    scene="collections",
                    use_state=use_state,
                )
                await self._click_profile_collections_tab(page)
                items = await self._collect_collection_items(page, limit=200)
                return {"folders": [], "items": items, "status": "ok"}

            return await self._run_with_scraper_session(p, action, viewport=DEFAULT_VIEWPORT)

    async def _click_search_user_tab(self, page: Page):
        # 搜索结果页的“用户”tab 经常改版：尽量用更宽松的选择器覆盖常见形态
        selectors = [
            "#user",
            "text=用户",
            "text=账号",
            "[role=tab]:has-text('用户')",
            "[role=tab]:has-text('账号')",
            "a:has-text('用户')",
            "a:has-text('账号')",
            "button:has-text('用户')",
            "button:has-text('账号')",
            "li:has-text('用户')",
            "li:has-text('账号')",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click(timeout=3000)
                    await self._random_sleep(1, 2)
                    return
            except Exception:
                continue

    async def _scroll_collect_profile_urls(self, page: Page, limit: int = 200) -> List[str]:
        collected = []
        seen = set()
        prev_height = 0
        for _ in range(2000):
            if len(collected) >= limit:
                break
            urls = await self._extract_profile_urls_from_page(page)
            for url in urls:
                if url in seen:
                    continue
                seen.add(url)
                collected.append(url)
                if len(collected) >= limit:
                    break
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await self._random_sleep(1.2, 2.2)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
            prev_height = new_height
        return collected

    async def _extract_profile_urls_from_page(self, page: Page) -> List[str]:
        urls: List[str] = []
        try:
            anchors = await page.locator("a[href*='/user/profile/']").all()
            for anchor in anchors:
                href = await anchor.get_attribute("href")
                if not href:
                    continue
                url = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
                url = self._normalize_url(url)
                if "/user/profile/" in url:
                    urls.append(url)
        except Exception:
            return []
        return urls

    async def _click_profile_collections_tab(self, page: Page):
        candidates = ["text=收藏", "a:has-text('收藏')", "button:has-text('收藏')"]
        for selector in candidates:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click(timeout=3000)
                    await self._random_sleep(1, 2)
                    return
            except Exception:
                continue

    async def _collect_collection_items(self, page: Page, limit: int = 200) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()
        prev_height = 0
        for _ in range(400):
            if len(items) >= limit:
                break
            cards = await page.locator("section.note-item, section[class*='note-item']").all()
            for card in cards:
                if len(items) >= limit:
                    break
                try:
                    cover = card.locator("a.cover").first
                    href = await cover.get_attribute("href") if await cover.count() > 0 else None
                    href = href or ""
                    if href and not href.startswith("http"):
                        href = f"https://www.xiaohongshu.com{href}"
                    note_id, canonical_url = self._canonicalize_note_url(href)
                    if not canonical_url or canonical_url in seen:
                        continue
                    seen.add(canonical_url)

                    title = ""
                    title_span = card.locator("a.title span").first
                    if await title_span.count() > 0:
                        title = await title_span.inner_text()
                    author = ""
                    author_span = card.locator(".author-wrapper span.name").first
                    if await author_span.count() > 0:
                        author = await author_span.inner_text()

                    items.append(
                        {
                            "note_id": note_id,
                            "url": canonical_url,
                            "title": self._normalize_whitespace(title)[:200],
                            "author": self._normalize_whitespace(author)[:80],
                            "saved_at": None,
                            "folder_name": None,
                        }
                    )
                except Exception:
                    continue
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await self._random_sleep(1.2, 2.2)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
            prev_height = new_height
        if items:
            return items
        try:
            html = await page.content()
            return self._parse_collection_items_from_html(html)[:limit]
        except Exception:
            return items

    async def fetch_profile(self, url: str) -> Optional[Dict[str, Any]]:
        """获取小红书用户主页信息。"""
        async with async_playwright() as p:
            normalized_url = self._normalize_url(url)
            for attempt in range(self.max_fetch_retries + 1):
                blocked = False
                has_error = False
                try:
                    async def action(page: Page, context: BrowserContext, use_state: bool) -> Dict[str, Any]:
                        logger.info(f"正在访问主页: {normalized_url}")
                        await self._open_page(
                            page,
                            normalized_url,
                            scene="profile",
                            use_state=use_state,
                            sleep_range=(3, 5),
                        )
                        title = await page.title()
                        profile = await self._extract_account_profile(page, normalized_url, fallback_display_name=title)
                        posts = await self.scroll_and_fetch_posts(page, limit=10)
                        if (
                            not posts
                            and title == "小红书 - 你的生活兴趣社区"
                            and not profile.get("xhs_id")
                            and not profile.get("display_name")
                        ):
                            logger.warning("页面返回通用标题且无帖子，疑似仍处于登录拦截。")
                            self._raise_login_block(
                                scene="profile",
                                reason="generic_title_without_posts",
                                use_state=use_state,
                            )
                        if use_state:
                            await self._persist_storage_state(context)
                        return {"url": normalized_url, "title": title, "posts": posts, "profile": profile}

                    return await self._run_with_scraper_session(p, action, viewport=DEFAULT_VIEWPORT)
                except LoginRequiredError:
                    # 登录拦截时不做无意义重试，交给上游刷新登录态。
                    raise
                except Exception as e:
                    has_error = True
                    logger.error(f"抓取失败: {e}")
                if not self._should_retry_fetch(attempt, blocked, has_error):
                    break
                wait_seconds = self.retry_backoff_seconds * (attempt + 1)
                logger.info(f"准备重试抓取，第 {attempt + 1} 次重试，等待 {wait_seconds:.1f} 秒")
                await asyncio.sleep(wait_seconds)
            logger.warning("多次抓取后仍失败，请重新运行 `python -m scripts.local_login` 更新登录状态。")
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
        posts: List[Dict[str, Any]] = []
        seen = set()
        prev_height = 0

        async def collect_from_anchors() -> None:
            anchors = await page.locator("a[href*='/explore/']").all()
            for a in anchors:
                if len(posts) >= limit:
                    break
                href = await a.get_attribute("href")
                if not href:
                    continue
                url = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
                url = self._normalize_url(url)
                note_id, canonical = self._canonicalize_note_url(url)
                canonical = canonical or url
                if not canonical or canonical in seen:
                    continue
                seen.add(canonical)

                title = ""
                try:
                    # 卡片上的标题往往在 a 的父级/子级里（覆盖文案）
                    title = self._normalize_whitespace(await a.inner_text())[:200]
                except Exception:
                    title = ""

                posts.append({"id": note_id or canonical.split("/")[-1], "title": title, "url": canonical})

        # 一些页面需要滚动触发懒加载，多滚几屏再收集
        for _ in range(60):
            if await self._check_login_block(page):
                break
            await collect_from_anchors()
            if len(posts) >= limit:
                break
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await self._random_sleep(1.2, 2.4)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
            prev_height = new_height

        return posts[:limit]

    async def fetch_note_detail(self, note_url: str, comments_limit: int = 0) -> Dict[str, Any]:
        """抓取单条笔记详情（图片 + 文案 + 可选评论）。"""
        async with async_playwright() as p:
            async def action(page: Page, _context: BrowserContext, use_state: bool) -> Dict[str, Any]:
                normalized = await self._open_page(
                    page,
                    note_url,
                    scene="note_detail",
                    use_state=use_state,
                    timeout=120000,
                    sleep_range=(2, 4),
                    wait_for_networkidle=True,
                )
                note_id, canonical = self._canonicalize_note_url(normalized)
                # 文案：优先取 meta（og:description/description），其次再用 DOM/JSON 兜底
                content_text = ""
                try:
                    meta_desc = await page.locator("meta[property='og:description']").get_attribute("content")
                    meta_desc = self._normalize_whitespace(html.unescape(meta_desc or ""))
                    if meta_desc:
                        content_text = meta_desc
                except Exception:
                    pass
                if not content_text:
                    try:
                        meta_desc = await page.locator("meta[name='description']").get_attribute("content")
                        meta_desc = self._normalize_whitespace(html.unescape(meta_desc or ""))
                        if meta_desc:
                            content_text = meta_desc
                    except Exception:
                        pass
                if not content_text:
                    for selector in [
                        "[class*='note'] [class*='desc']",
                        "[class*='desc']",
                        "[class*='note-content']",
                        "[class*='content']",
                        "article",
                        "main",
                    ]:
                        try:
                            loc = page.locator(selector).first
                            if await loc.count() > 0:
                                txt = self._normalize_whitespace(await loc.inner_text())
                                if txt and len(txt) > len(content_text):
                                    content_text = txt
                        except Exception:
                            continue

                # 图片：抓页面里可见的高频图片 src（过滤掉头像/图标）
                image_urls: List[str] = []
                try:
                    # 1) meta og:image 先拿一张封面（很多笔记页都会有）
                    og_img = await page.locator("meta[property='og:image']").get_attribute("content")
                    og_img = (og_img or "").strip()
                    if og_img:
                        image_urls.append(og_img)
                except Exception:
                    pass
                try:
                    imgs = await page.locator("img").all()
                    for img in imgs:
                        src = await img.get_attribute("src") or await img.get_attribute("data-src") or await img.get_attribute("data-lazy-src")
                        if not src:
                            continue
                        src = src.strip()
                        if src.startswith("data:"):
                            continue
                        # 过滤明显的 UI 图标
                        if any(token in src for token in ["avatar", "icon", "logo"]):
                            continue
                        # 小红书图片域名常见关键字（兜底）
                        if any(token in src for token in ["xhsimg", "xhscdn", "sns-img", "ali-cnfs"]):
                            image_urls.append(src)
                    # 去重
                    dedup = []
                    seen_img = set()
                    for u in image_urls:
                        if u in seen_img:
                            continue
                        seen_img.add(u)
                        dedup.append(u)
                    image_urls = dedup[:30]
                except Exception:
                    image_urls = []

                # JSON 兜底：有些页面的文案/图片不会直接出现在文本/IMG src 中
                if not content_text or not image_urls:
                    try:
                        next_data = await page.locator("script#__NEXT_DATA__").first.inner_text()
                        payload = json.loads(next_data)

                        texts: List[str] = []
                        urls: List[str] = []

                        def walk(node):
                            if isinstance(node, dict):
                                for k, v in node.items():
                                    if isinstance(v, str):
                                        if k.lower() in {"desc", "description", "content", "text", "title"}:
                                            texts.append(v)
                                        if any(tok in v for tok in ["xhsimg", "xhscdn", "sns-img", "ali-cnfs"]):
                                            urls.append(v)
                                    else:
                                        walk(v)
                            elif isinstance(node, list):
                                for it in node:
                                    walk(it)

                        walk(payload)
                        if not content_text and texts:
                            candidate = max((self._normalize_whitespace(t) for t in texts), key=lambda x: len(x), default="")
                            if candidate:
                                content_text = candidate
                        if urls:
                            image_urls = list(dict.fromkeys(image_urls + [u.strip() for u in urls if isinstance(u, str) and u.strip()]))[:30]
                    except Exception:
                        pass

                # 评论（可选）：以“评论区块”为粒度收集前 N 条文本
                comments: List[Dict[str, Any]] = []
                if comments_limit > 0:
                    try:
                        # 多数页面会有 comment 相关 class；这里用宽松匹配
                        items = await page.locator("[class*='comment']").all()
                        for item in items:
                            if len(comments) >= comments_limit:
                                break
                            try:
                                txt = self._normalize_whitespace(await item.inner_text())
                                # 过滤掉“展开/收起/共xx条”等非评论文本
                                if not txt or "评论" == txt or "展开" in txt:
                                    continue
                                comments.append({"text": txt[:800]})
                            except Exception:
                                continue
                    except Exception:
                        comments = []

                return {
                    "note_id": note_id,
                    "url": canonical or normalized,
                    "content_text": content_text[:5000],
                    "image_urls": image_urls,
                    "comments": comments,
                }

            return await self._run_with_scraper_session(p, action, viewport=DETAIL_VIEWPORT)

    def _extract_account_id_from_url(self, account_url: str) -> str:
        parsed = urlparse(account_url)
        path = parsed.path.strip("/")
        if not path:
            return ""
        return path.split("/")[-1]

    def _canonicalize_note_url(self, url: str) -> Tuple[str, str]:
        normalized = self._normalize_url(url)
        if not normalized:
            return "", ""
        parsed = urlparse(normalized)
        path = parsed.path.strip("/")
        parts = path.split("/") if path else []
        note_id = ""
        if "explore" in parts:
            idx = parts.index("explore")
            if idx + 1 < len(parts):
                note_id = parts[idx + 1]
        elif len(parts) >= 2 and parts[0] == "user" and parts[1] == "profile":
            note_id = parts[-1]
        if note_id:
            return note_id, f"https://www.xiaohongshu.com/explore/{note_id}"
        return "", normalized

    def _parse_collection_items_from_html(self, html: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        seen = set()
        for match in re.finditer(r'<section[^>]*class="[^"]*note-item[^"]*"[\s\S]*?</section>', html or ""):
            block = match.group(0)
            # 兼容两种情况：
            # 1) href 自带 xsec_source=pc_collect 等 query（常见于收藏页）
            # 2) 直接是 /explore/<note_id> 链接
            href_match = re.search(r'href="([^"]+)"', block)
            href = href_match.group(1) if href_match else ""
            if href and not href.startswith("http"):
                href = f"https://www.xiaohongshu.com{href}"
            note_id, canonical_url = self._canonicalize_note_url(href)
            if not canonical_url or canonical_url in seen:
                continue
            seen.add(canonical_url)

            title_match = re.search(r'<a[^>]*class="title"[^>]*>[\s\S]*?<span[^>]*>([^<]+)</span>', block)
            title = self._normalize_whitespace(title_match.group(1)) if title_match else ""
            author_match = re.search(r'<span[^>]*class="name"[^>]*>([^<]+)</span>', block)
            author_name = self._normalize_whitespace(author_match.group(1)) if author_match else ""
            items.append(
                {
                    "note_id": note_id,
                    "url": canonical_url,
                    "title": title[:200],
                    "author": author_name[:80],
                    "saved_at": None,
                    "folder_name": None,
                }
            )
        return items

if __name__ == "__main__":
    # 示例用法
    async def main():
        scraper = XiaohongshuScraper(headless=True)
        # 如果是第一次在本地运行，请取消下面这行的注释来扫码登录：
        # await scraper.login_and_save_state()
        await scraper.fetch_profile("https://www.xiaohongshu.com/user/profile/5b15392b4260905102559902")
    asyncio.run(main())
