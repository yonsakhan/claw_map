"""Legacy project entrypoint.

Use `src.crawler.run_large_scale_crawl` for the maintained crawl entrypoint.
This top-level module remains as a thin compatibility wrapper.
"""

import logging

from src.crawler import run_large_scale_crawl


logger = logging.getLogger("MainCompat")


def main():
    logger.warning("root main.py is deprecated; delegating to src.crawler.run_large_scale_crawl.")
    run_large_scale_crawl.main()


def run_cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()


if __name__ == "__main__":
    run_cli()
