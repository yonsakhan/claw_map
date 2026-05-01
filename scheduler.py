"""Legacy top-level scheduler entrypoint.

Use `src.crawler.scheduler` for the maintained implementation.
This module remains as a thin compatibility wrapper.
"""

from src.crawler.scheduler import CrawlTask, Scheduler

__all__ = ["Scheduler", "CrawlTask"]
