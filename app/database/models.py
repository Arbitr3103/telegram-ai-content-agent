"""
Database models for Telegram AI Content Agent
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Source(Base):
    """Source model for collected articles/news"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False)  # 'exa_news', 'habr', 'telegram', 'api_docs'
    title = Column(String(500), nullable=False)
    content = Column(Text)
    url = Column(String(1000), unique=True)
    published_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.5)
    extra_data = Column(JSONB, default={})


class Post(Base):
    """Post model for generated content"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(String), default=[])
    sources = Column(JSONB, default=[])  # Array of {name, url}
    generated_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
    status = Column(String(20), default='draft')  # draft, scheduled, published
    telegram_message_id = Column(Integer)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    schedule = relationship("Schedule", back_populates="post", uselist=False)
    stats = relationship("PostStats", back_populates="post", uselist=False)


class Schedule(Base):
    """Schedule model for post publication timing"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True)
    scheduled_for = Column(DateTime, nullable=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="schedule")


class PostStats(Base):
    """PostStats model for engagement tracking"""
    __tablename__ = "post_stats"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True)
    views = Column(Integer, default=0)
    reactions = Column(Integer, default=0)
    forwards = Column(Integer, default=0)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    history = Column(JSONB, default=[])  # Array tracking stats over time

    # Relationships
    post = relationship("Post", back_populates="stats")
