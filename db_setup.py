import os
import sys

sys.path.append(os.getcwd())

from src.models.base import Base
from src.models.user import UserProfile, UserPost
from src.models.persona import AgentPersona
from src.db.session import get_engine
from src.config import settings

def init_db():
    print(f"Initializing database at {settings.postgres_url}...")
    engine = get_engine()
    print("Creating tables for UserProfile, UserPost and AgentPersona...")
    Base.metadata.create_all(engine)
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
