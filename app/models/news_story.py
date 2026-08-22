"""
NewsStory SQLAlchemy Model
Matches public.news_stories schema in Supabase exactly
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class NewsStory(Base):
    """News story detected from various sources"""

    __tablename__ = "news_stories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source information
    source_id = Column(UUID(as_uuid=True), ForeignKey("news_sources.id", ondelete="CASCADE"), nullable=False)
    source_name = Column(Text, nullable=False)

    # Original content (from source)
    original_url = Column(Text, nullable=False)
    original_title = Column(Text, nullable=False)
    original_author = Column(Text)
    original_content = Column(Text)
    original_summary = Column(Text)
    original_image_url = Column(Text)
    published_at = Column(DateTime(timezone=True))

    # Flobstar-processed content
    flobstar_headline = Column(Text)
    flobstar_summary = Column(Text)
    flobstar_content = Column(Text)
    flobstar_category = Column(Text)
    flobstar_tags = Column(ARRAY(Text))
    flobstar_priority = Column(Text)
    relevance_score = Column(Float)
    geographic_relevance = Column(Text)

    # Image management
    selected_image_url = Column(Text)
    image_caption = Column(Text)
    image_credit = Column(Text)
    image_alt_text = Column(Text)

    # Classification and status
    category = Column(Text)
    priority = Column(String(20), default="routine")
    status = Column(
        String(50),
        nullable=False,
        default="detected",
        server_default="detected"
    )
    language = Column(Text, default="en")

    # Duplicate detection
    duplicate_group = Column(UUID(as_uuid=True))
    is_duplicate = Column(Boolean, default=False)
    duplicate_similarity_score = Column(Float)

    # Attribution
    source_attribution = Column(Text)
    ai_generated = Column(Boolean, default=False)
    ai_model_used = Column(Text)

    # Processing timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    ai_draft_generated_at = Column(DateTime(timezone=True))
    published_at_flobstar = Column(DateTime(timezone=True))

    # Metadata timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Aliases/helpers for backward compatibility
    @property
    def original_headline(self):
        return self.original_title

    @original_headline.setter
    def original_headline(self, val):
        self.original_title = val

    def __repr__(self):
        return f"<NewsStory(id={self.id}, title={self.original_title}, status={self.status})>"
