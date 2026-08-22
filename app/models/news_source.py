"""
NewsSource model
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class NewsSource(Base):
    """News source configuration for RSS feeds, APIs, and web scrapers"""

    __tablename__ = "news_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    website_url = Column(Text)
    feed_url = Column(Text)
    source_type = Column(
        String(50),
        nullable=False,
        default="RSS",
        server_default="RSS"
    )
    country = Column(String(100), default="Global")
    region = Column(String(100))
    category = Column(String(100), default="General")
    language = Column(String(10), default="en")
    priority = Column(String(20), default="medium")
    polling_interval_minutes = Column(Integer, default=15)
    status = Column(
        String(50),
        nullable=False,
        default="active",
        server_default="active"
    )
    description = Column(Text)

    # Health tracking
    last_successful_check = Column(DateTime(timezone=True))
    last_failed_check = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)
    last_successful_item = Column(DateTime(timezone=True))
    response_time_ms = Column(Integer)
    total_stories_collected = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255))

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('RSS', 'ATOM', 'API', 'WEB_SCRAPER', 'PRESS_RELEASE', 'CUSTOM')",
            name="valid_source_type"
        ),
        CheckConstraint(
            "status IN ('active', 'disabled', 'archived')",
            name="valid_status"
        ),
        CheckConstraint(
            "priority IN ('high', 'medium', 'low')",
            name="valid_priority"
        ),
    )

    def __repr__(self):
        return f"<NewsSource(id={self.id}, name={self.name}, type={self.source_type})>"
