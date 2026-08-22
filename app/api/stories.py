"""
API endpoints for news stories
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.news_story import NewsStory

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_stories(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    is_duplicate: Optional[bool] = None,
    ai_generated: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all news stories with optional filtering
    """
    query = select(NewsStory)

    if status and status != 'all':
        query = query.where(NewsStory.status == status)
    if priority and priority != 'all':
        query = query.where(NewsStory.priority == priority)
    if category and category != 'all':
        query = query.where(NewsStory.category == category)
    if is_duplicate is not None:
        query = query.where(NewsStory.is_duplicate == is_duplicate)
    if ai_generated is not None:
        query = query.where(NewsStory.ai_generated == ai_generated)

    query = query.order_by(NewsStory.detected_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    stories = result.scalars().all()

    return [
        {
            "id": str(story.id),
            "source_id": str(story.source_id) if story.source_id else None,
            "source_name": story.source_name,
            "original_url": story.original_url,
            "original_headline": story.original_title,
            "flobstar_headline": story.flobstar_headline or story.original_title,
            "flobstar_summary": story.flobstar_summary or story.original_summary,
            "category": story.category,
            "geographic_relevance": story.geographic_relevance,
            "priority": story.priority,
            "status": story.status,
            "is_duplicate": story.is_duplicate,
            "ai_generated": story.ai_generated,
            "detected_at": story.detected_at.isoformat() if story.detected_at else None,
            "processed_at": story.processed_at.isoformat() if story.processed_at else None,
            "ai_draft_generated_at": story.ai_draft_generated_at.isoformat() if story.ai_draft_generated_at else None,
            "published_at_flobstar": story.published_at_flobstar.isoformat() if story.published_at_flobstar else None,
            "flobstar_tags": story.flobstar_tags,
        }
        for story in stories
    ]


@router.get("/{story_id}", response_model=dict)
async def get_story(story_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific news story by ID
    """
    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return {
        "id": str(story.id),
        "source_id": str(story.source_id) if story.source_id else None,
        "source_name": story.source_name,
        "original_url": story.original_url,
        "original_headline": story.original_title,
        "original_summary": story.original_summary,
        "original_content": story.original_content,
        "original_author": story.original_author,
        "original_published_at": story.published_at.isoformat() if story.published_at else None,
        "flobstar_headline": story.flobstar_headline or story.original_title,
        "flobstar_summary": story.flobstar_summary or story.original_summary,
        "flobstar_content": story.flobstar_content,
        "category": story.category,
        "geographic_relevance": story.geographic_relevance,
        "flobstar_tags": story.flobstar_tags,
        "priority": story.priority,
        "status": story.status,
        "is_duplicate": story.is_duplicate,
        "ai_generated": story.ai_generated,
        "detected_at": story.detected_at.isoformat() if story.detected_at else None,
        "processed_at": story.processed_at.isoformat() if story.processed_at else None,
        "ai_draft_generated_at": story.ai_draft_generated_at.isoformat() if story.ai_draft_generated_at else None,
        "published_at_flobstar": story.published_at_flobstar.isoformat() if story.published_at_flobstar else None,
        "published_article_id": story.published_article_id,
        "created_at": story.created_at.isoformat() if story.created_at else None,
        "updated_at": story.updated_at.isoformat() if story.updated_at else None,
    }


@router.post("/", response_model=dict, status_code=201)
async def create_story(story_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Create a new news story
    """
    new_story = NewsStory(
        source_id=story_data.get("source_id"),
        source_name=story_data.get("source_name", "Direct Entry"),
        original_url=story_data.get("original_url"),
        original_title=story_data.get("original_headline") or story_data.get("original_title", "Untitled"),
        original_summary=story_data.get("original_summary"),
        original_content=story_data.get("original_content"),
        original_author=story_data.get("original_author"),
        published_at=story_data.get("original_published_at") or story_data.get("published_at"),
        flobstar_headline=story_data.get("flobstar_headline"),
        flobstar_summary=story_data.get("flobstar_summary"),
        flobstar_content=story_data.get("flobstar_content"),
        category=story_data.get("category"),
        geographic_relevance=story_data.get("geographic_relevance"),
        flobstar_tags=story_data.get("flobstar_tags"),
        priority=story_data.get("priority", "routine"),
        status=story_data.get("status", "detected"),
        is_duplicate=story_data.get("is_duplicate", False),
        ai_generated=story_data.get("ai_generated", False),
    )

    db.add(new_story)
    await db.commit()
    await db.refresh(new_story)

    return {
        "id": str(new_story.id),
        "original_headline": new_story.original_title,
        "status": new_story.status,
        "detected_at": new_story.detected_at.isoformat() if new_story.detected_at else None,
    }


@router.put("/{story_id}", response_model=dict)
async def update_story(story_id: str, story_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Update an existing news story
    """
    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    for field, value in story_data.items():
        if hasattr(story, field) and field not in ["id", "created_at", "detected_at"]:
            setattr(story, field, value)

    await db.commit()
    await db.refresh(story)

    return {
        "id": str(story.id),
        "status": story.status,
        "updated_at": story.updated_at.isoformat() if story.updated_at else None,
    }


@router.patch("/{story_id}/status", response_model=dict)
async def update_story_status(story_id: str, status_data: dict, db: AsyncSession = Depends(get_db)):
    """
    Update the status of a news story
    """
    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    new_status = status_data.get("status")
    if new_status:
        story.status = new_status

    await db.commit()
    await db.refresh(story)

    return {
        "id": str(story.id),
        "status": story.status,
        "updated_at": story.updated_at.isoformat() if story.updated_at else None,
    }


@router.delete("/{story_id}", response_model=dict)
async def delete_story(story_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete (archive) a news story
    """
    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.status = "archived"
    await db.commit()

    return {
        "id": str(story.id),
        "status": "archived",
        "message": "Story archived successfully"
    }


@router.get("/stats/dashboard", response_model=dict)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard statistics for news stories
    """
    status_counts = await db.execute(
        select(NewsStory.status, func.count(NewsStory.id))
        .group_by(NewsStory.status)
    )
    status_stats = {status: count for status, count in status_counts.all()}

    priority_counts = await db.execute(
        select(NewsStory.priority, func.count(NewsStory.id))
        .group_by(NewsStory.priority)
    )
    priority_stats = {priority: count for priority, count in priority_counts.all()}

    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_count = await db.execute(
        select(func.count(NewsStory.id))
        .where(NewsStory.detected_at >= twenty_four_hours_ago)
    )
    recent_stories_count = recent_count.scalar() or 0

    breaking_count = await db.execute(
        select(func.count(NewsStory.id))
        .where(NewsStory.priority == "breaking", NewsStory.status.in_(["detected", "processing", "ai_draft_ready", "assigned", "under_review"]))
    )
    breaking_stories_count = breaking_count.scalar() or 0

    return {
        "total_stories": sum(status_stats.values()),
        "by_status": status_stats,
        "by_priority": priority_stats,
        "recent_24h": recent_stories_count,
        "breaking_stories": breaking_stories_count,
    }
