from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    bio = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    posts = relationship("UserPost", back_populates="user")

    def __repr__(self):
        return f"<UserProfile(username='{self.username}')>"

class UserPost(Base):
    __tablename__ = 'user_posts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_profiles.id'), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("UserProfile", back_populates="posts")

    def __repr__(self):
        return f"<UserPost(id={self.id}, user_id={self.user_id})>"
