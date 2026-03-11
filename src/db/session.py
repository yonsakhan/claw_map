from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings


def get_engine():
    return create_engine(settings.postgres_url, echo=True)


def get_session_factory():
    return sessionmaker(bind=get_engine())
