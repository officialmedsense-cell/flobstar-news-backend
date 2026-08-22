"""
SourceHealthHistory model
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class SourceHealthHistory(Base):
    """Historical health data for news sources"""

    __tablename__ = "source_health_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("news_sources.id", ondelete="CASCADE"), nullable=False)

    # Health status at time of check
    health_status = Column(String(50), nullable=False)
    response_time_ms = Column(Integer)
    stories_found = Column(Integer, default=0)
    error_message = Column(Text)

    # Timestamp
    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "health_status IN ('healthy', 'warning', 'error', 'disabled')",
            name="valid_health_status"
        ),
    )

    def __repr__(self):
        return f"<SourceHealthHistory(id={self.id}, source_id={self.source_id}, status={self.health_status})>"
