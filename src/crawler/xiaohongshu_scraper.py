import asyncio
import random
import logging
import os
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, BrowserContext
from fake_useragent import UserAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("XiaohongshuScraper")

class XiaohongshuScraper:
    def __init__(self, headless: bool = True, storage_state_path: str = "src/storage/xhs_state.json"):
        self.headless = headless
        self.ua = UserAgent()
        self.storage_state_path = storage_state_path

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

    async def login_and_save_state(self):
        """手动登录并保存状态到本地文件。"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # 本地运行必须开启界面用于扫码
            context = await browser.new_context(
                user_agent=await self._get_random_user_agent(),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            logger.info("请在打开的浏览器窗口中完成小红书登录（扫码等）...")
            await page.goto("https://www.xiaohongshu.com")
            
            try:
                # 等待登录成功的标志（侧边栏出现通常意味着登录成功）
                await page.wait_for_selector(".side-bar-container", timeout=120000)
                logger.info("登录成功，正在保存状态...")
                
                # 确保目录存在
                os.makedirs(os.path.dirname(self.storage_state_path), exist_ok=True)
                
                await context.storage_state(path=self.storage_state_path)
                logger.info(f"状态已保存至: {self.storage_state_path}")
            except Exception as e:
                logger.error(f"登录超时或失败: {e}")
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
            return False
        except Exception:
            return False

    async def fetch_profile(self, url: str) -> Optional[Dict[str, Any]]:
        """获取小红书用户主页信息。"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # 尝试加载已保存的登录状态
            storage_state = None
            if os.path.exists(self.storage_state_path):
                storage_state = self.storage_state_path
                logger.info(f"使用保存的登录状态: {self.storage_state_path}")
            
            context = await browser.new_context(
                storage_state=storage_state,
                user_agent=await self._get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            
            # 绕过 WebDriver 检测
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = await context.new_page()
            try:
                logger.info(f"正在访问主页: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await self._random_sleep(3, 5)

                if await self._check_login_block(page):
                    logger.warning("检测到登录拦截！请确保已运行登录脚本保存状态。")
                    return None
                
                title = await page.title()
                posts = await self.scroll_and_fetch_posts(page, limit=10)
                
                return {"url": url, "title": title, "posts": posts}
            except Exception as e:
                logger.error(f"抓取失败: {e}")
                return None
            finally:
                await browser.close()

    async def scroll_and_fetch_posts(self, page: Page, limit: int = 10) -> List[Dict[str, Any]]:
        """滚动并解析帖子。"""
        posts = []
        note_selector = ".note-item"
        prev_height = 0
        
        while len(posts) < limit:
            if await self._check_login_block(page): break
            
            elements = await page.locator(note_selector).all()
            for el in elements:
                if len(posts) >= limit: break
                try:
                    title_el = el.locator(".title")
                    link_el = el.locator("a.cover")
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

if __name__ == "__main__":
    # 示例用法
    async def main():
        scraper = XiaohongshuScraper(headless=True)
        # 如果是第一次在本地运行，请取消下面这行的注释来扫码登录：
        # await scraper.login_and_save_state()
        await scraper.fetch_profile("https://www.xiaohongshu.com/user/profile/5b15392b4260905102559902")
    asyncio.run(main())
