"""
StoryStatusHistory model
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class StoryStatusHistory(Base):
    """History of status changes for news stories"""

    __tablename__ = "story_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("news_stories.id", ondelete="CASCADE"), nullable=False)

    # Status change details
    old_status = Column(String(50))
    new_status = Column(String(50), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))

    # Change context
    change_reason = Column(Text)
    notes = Column(Text)
    status_metadata = Column(Text)

    # Timestamp
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<StoryStatusHistory(id={self.id}, story_id={self.story_id}, old={self.old_status}, new={self.new_status})>"
