"""
StoryAssignment model
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class StoryAssignment(Base):
    """Assignment of stories to editors/writers"""

    __tablename__ = "story_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("news_stories.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))

    # Assignment details
    assignment_type = Column(String(50), default="editorial")
    priority = Column(String(20), default="routine")
    status = Column(
        String(50),
        nullable=False,
        default="assigned",
        server_default="assigned"
    )
    deadline = Column(DateTime(timezone=True))

    # Acceptance timestamps
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Assignment notes
    notes = Column(Text)
    rejection_reason = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "assignment_type IN ('editorial', 'fact_check', 'rewrite', 'review')",
            name="valid_assignment_type"
        ),
        CheckConstraint(
            "priority IN ('breaking', 'important', 'routine')",
            name="valid_priority"
        ),
        CheckConstraint(
            "status IN ('assigned', 'accepted', 'completed', 'rejected', 'cancelled')",
            name="valid_status"
        ),
    )

    def __repr__(self):
        return f"<StoryAssignment(id={self.id}, story_id={self.story_id}, assigned_to={self.assigned_to}, status={self.status})>"
