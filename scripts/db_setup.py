"""Database initialization and lightweight schema backfill script."""

import logging

from sqlalchemy import inspect, text

from src.config import settings
from src.db.session import get_engine
from src.models.base import Base
from src.models.persona import AgentPersona
from src.models.user import UserPost, UserProfile


logger = logging.getLogger("DBSetup")

# Import model modules so SQLAlchemy metadata includes these tables before create_all().
_REGISTERED_MODELS = (UserProfile, UserPost, AgentPersona)

AGENT_PERSONAS_REQUIRED_COLUMNS = {
    "questionnaire_answers": "JSON",
    "reasoning_summary": "VARCHAR",
    "prompt_version": "VARCHAR",
    "questionnaire_version": "VARCHAR",
    "model_params": "JSON",
    "feature_snapshot": "JSON",
    "evidence_references": "JSON",
    "created_at": "TIMESTAMP",
}


def migrate_agent_personas_columns(engine):
    inspector = inspect(engine)
    if "agent_personas" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("agent_personas")}
    with engine.begin() as connection:
        for column_name, column_type in AGENT_PERSONAS_REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                text(
                    f'ALTER TABLE "agent_personas" '
                    f'ADD COLUMN "{column_name}" {column_type}'
                )
            )
            logger.info("Added missing column agent_personas.%s", column_name)


def init_db():
    logger.info("Initializing database at %s", settings.postgres_url)
    engine = get_engine()
    logger.info("Creating tables for UserProfile, UserPost and AgentPersona...")
    Base.metadata.create_all(engine)
    migrate_agent_personas_columns(engine)
    logger.info("Database initialization completed successfully.")


def main():
    init_db()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
