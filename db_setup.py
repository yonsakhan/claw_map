"""Legacy top-level database setup entrypoint."""

import logging

from scripts import db_setup as _impl

AGENT_PERSONAS_REQUIRED_COLUMNS = _impl.AGENT_PERSONAS_REQUIRED_COLUMNS
_REGISTERED_MODELS = _impl._REGISTERED_MODELS
migrate_agent_personas_columns = _impl.migrate_agent_personas_columns
init_db = _impl.init_db
main = _impl.main
logger = logging.getLogger("DBSetupCompat")


def run_cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.warning("root db_setup.py is deprecated; use `python -m scripts.db_setup`.")
    main()


if __name__ == "__main__":
    run_cli()
