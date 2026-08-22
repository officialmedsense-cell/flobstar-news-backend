"""
AIGeneration model
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AIGeneration(Base):
    """AI-generated content for news stories"""

    __tablename__ = "ai_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("news_stories.id", ondelete="CASCADE"), nullable=False)

    # Generation details
    generation_type = Column(String(50), nullable=False)
    model_used = Column(String(100))
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending"
    )

    # Input/Output
    input_prompt = Column(Text)
    generated_content = Column(Text)
    generated_headline = Column(Text)
    generated_summary = Column(Text)

    # Quality metrics
    quality_score = Column(Integer)
    confidence_score = Column(Integer)
    processing_time_ms = Column(Integer)

    # Flags
    requires_human_review = Column(Boolean, default=True)
    approved_for_publication = Column(Boolean, default=False)

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Metadata
    generation_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "generation_type IN ('headline', 'summary', 'full_article', 'rewrite', 'fact_check')",
            name="valid_generation_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="valid_status"
        ),
    )

    def __repr__(self):
        return f"<AIGeneration(id={self.id}, story_id={self.story_id}, type={self.generation_type}, status={self.status})>"
