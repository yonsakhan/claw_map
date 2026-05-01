"""Legacy top-level local login entrypoint."""

import asyncio
import logging

from scripts import local_login as _impl

_parse_args = _impl._parse_args
_resolve_login_options = _impl._resolve_login_options
main = _impl.main
logger = logging.getLogger("LocalLoginCompat")


def run_cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.warning("root local_login.py is deprecated; use `python -m scripts.local_login`.")
    asyncio.run(main())


if __name__ == "__main__":
    run_cli()
