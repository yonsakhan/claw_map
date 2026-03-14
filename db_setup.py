import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import inspect, text

from src.models.base import Base
from src.models.user import UserProfile, UserPost
from src.models.persona import AgentPersona
from src.db.session import get_engine
from src.config import settings

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
            print(f"Added missing column agent_personas.{column_name}")


def init_db():
    print(f"Initializing database at {settings.postgres_url}...")
    engine = get_engine()
    print("Creating tables for UserProfile, UserPost and AgentPersona...")
    Base.metadata.create_all(engine)
    migrate_agent_personas_columns(engine)
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
