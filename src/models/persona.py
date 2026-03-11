from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from .base import Base


class AgentPersona(Base):
    __tablename__ = "agent_personas"

    id = Column(Integer, primary_key=True)
    original_id = Column(String, index=True, nullable=False)
    age_group = Column(String)
    location = Column(String)
    fertility_status = Column(String)
    income_level = Column(String)
    spatial_preferences = Column(JSON)
    fertility_intent_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
