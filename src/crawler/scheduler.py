import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

from src.crawler.xiaohongshu_scraper import XiaohongshuScraper
from src.storage.crawl_task_store import CrawlTaskStore


logger = logging.getLogger("CrawlScheduler")


@dataclass
class SeedConfig:
    explore_limit: int = 200
    search_keywords: Optional[List[str]] = None
    search_limit_per_keyword: int = 500


class CrawlScheduler:
    def __init__(self, task_store: Optional[CrawlTaskStore] = None, headless: bool = True):
        self.task_store = task_store or CrawlTaskStore()
        self.scraper = XiaohongshuScraper(headless=headless)

    async def seed(self, config: SeedConfig) -> int:
        total = 0
        if config.explore_limit > 0:
            seeded = await self._seed_from_explore(limit=config.explore_limit)
            total += seeded
        if config.search_keywords:
            for keyword in config.search_keywords:
                seeded = await self._seed_from_search(keyword=keyword, limit=config.search_limit_per_keyword)
                total += seeded
        return total

    async def _seed_from_explore(self, limit: int) -> int:
        accounts = await self.scraper.collect_accounts_from_explore(limit=limit)
        inserted = 0
        for item in accounts:
            profile = item.get("profile", {}) or {}
            url = profile.get("profile_url") or item.get("account_url") or ""
            if not url:
                continue
            self.task_store.enqueue_url(
                url=url,
                task_type="user_profile",
                payload={"account_id": item.get("account_id", ""), "source_entry": "explore"},
                source_entry="explore",
                priority=1,
            )
            inserted += 1
        logger.info(f"Seeded from explore: {inserted}")
        return inserted

    async def _seed_from_search(self, keyword: str, limit: int) -> int:
        keyword = str(keyword)
        encoded = quote(keyword)
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded}&source=web_search_result_notes"
        accounts = await self.scraper.collect_accounts_from_search(search_url=search_url, limit=limit)
        inserted = 0
        for url in accounts:
            self.task_store.enqueue_url(
                url=url,
                task_type="user_profile",
                payload={"account_id": "", "source_entry": f"search:{keyword}"},
                source_entry=f"search:{keyword}",
                priority=0,
            )
            inserted += 1
        logger.info(f"Seeded from search '{keyword}': {inserted}")
        return inserted

