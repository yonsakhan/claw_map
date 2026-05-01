"""Legacy top-level worker entrypoint.

Use `src.crawler.worker` for the maintained implementation.
This module remains as a thin compatibility wrapper.
"""

import logging

from src.crawler import worker as crawler_worker


logger = logging.getLogger("WorkerCompat")
run_serial = crawler_worker.run_serial
_src_main = crawler_worker.main


def main():
    logger.warning("root worker.py is deprecated; delegating to src.crawler.worker.")
    _src_main()


def run_cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()


if __name__ == "__main__":
    run_cli()
