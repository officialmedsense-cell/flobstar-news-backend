"""
AuditLog model
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AuditLog(Base):
    """Comprehensive activity tracking for newsroom accountability"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor information
    actor_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    actor_type = Column(String(50), nullable=False)
    actor_email = Column(String(255))
    actor_name = Column(String(255))

    # Action details
    action_type = Column(String(100), nullable=False)
    action_category = Column(String(50), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(UUID(as_uuid=True))

    # Action details
    description = Column(Text, nullable=False)
    details = Column(JSONB)

    # Related entities
    story_id = Column(UUID(as_uuid=True), ForeignKey("news_stories.id", ondelete="SET NULL"))
    source_id = Column(UUID(as_uuid=True), ForeignKey("news_sources.id", ondelete="SET NULL"))
    assignment_id = Column(UUID(as_uuid=True))

    # Change tracking
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changed_fields = Column(ARRAY(String))

    # Request context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_id = Column(String(100))

    # Result
    status = Column(String(50), nullable=False, default="success", server_default="success")
    error_message = Column(Text)
    error_code = Column(String(50))

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Metadata
    audit_metadata = Column(JSONB)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action_type}, actor={self.actor_type}, status={self.status})>"
