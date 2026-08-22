"""
NewsNotification model
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class NewsNotification(Base):
    """Notifications for newsroom users"""

    __tablename__ = "news_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)

    # Notification details
    notification_type = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")

    # Related entities
    story_id = Column(UUID(as_uuid=True), ForeignKey("news_stories.id", ondelete="SET NULL"))
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("story_assignments.id", ondelete="SET NULL"))
    source_id = Column(UUID(as_uuid=True), ForeignKey("news_sources.id", ondelete="SET NULL"))

    # Action
    action_url = Column(Text)
    action_label = Column(Text)

    # Delivery
    channels = Column(ARRAY(String), default=["in_app"])
    delivery_status = Column(String(50), default="pending")

    # Read status
    read_at = Column(DateTime(timezone=True))
    read_status = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('story_assigned', 'story_updated', 'source_error', 'system_alert', 'ai_ready', 'approval_needed')",
            name="valid_notification_type"
        ),
        CheckConstraint(
            "priority IN ('urgent', 'high', 'normal', 'low')",
            name="valid_priority"
        ),
        CheckConstraint(
            "delivery_status IN ('pending', 'sent', 'delivered', 'failed')",
            name="valid_delivery_status"
        ),
    )

    def __repr__(self):
        return f"<NewsNotification(id={self.id}, recipient_id={self.recipient_id}, type={self.notification_type}, read={self.read_status})>"
