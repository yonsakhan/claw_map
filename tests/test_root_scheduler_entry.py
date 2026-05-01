import unittest

import scheduler
from src.crawler.scheduler import CrawlTask as SrcCrawlTask
from src.crawler.scheduler import Scheduler as SrcScheduler


class TestRootSchedulerEntry(unittest.TestCase):
    def test_root_scheduler_reexports_src_scheduler(self):
        self.assertIs(scheduler.Scheduler, SrcScheduler)

    def test_root_scheduler_reexports_src_crawl_task(self):
        self.assertIs(scheduler.CrawlTask, SrcCrawlTask)


if __name__ == "__main__":
    unittest.main()
