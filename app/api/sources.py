"""
API endpoints for news sources
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_user, require_service_role
from app.models.news_source import NewsSource
from app.models.source_health_history import SourceHealthHistory

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_sources(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all news sources with optional filtering
    """
    query = select(NewsSource)

    if status:
        query = query.where(NewsSource.status == status)
    if source_type:
        query = query.where(NewsSource.source_type == source_type)
    if category:
        query = query.where(NewsSource.category == category)

    query = query.order_by(NewsSource.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    sources = result.scalars().all()

    return [
        {
            "id": str(source.id),
            "name": source.name,
            "website_url": source.website_url,
            "feed_url": source.feed_url,
            "source_type": source.source_type,
            "country": source.country,
            "category": source.category,
            "language": source.language,
            "priority": source.priority,
            "status": source.status,
            "description": source.description,
            "last_successful_check": source.last_successful_check.isoformat() if source.last_successful_check else None,
            "consecutive_failures": source.consecutive_failures,
            "total_stories_collected": source.total_stories_collected,
            "created_at": source.created_at.isoformat() if source.created_at else None,
        }
        for source in sources
    ]


@router.get("/{source_id}", response_model=dict)
async def get_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific news source by ID
    """
    query = select(NewsSource).where(NewsSource.id == source_id)
    result = await db.execute(query)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return {
        "id": str(source.id),
        "name": source.name,
        "website_url": source.website_url,
        "feed_url": source.feed_url,
        "source_type": source.source_type,
        "country": source.country,
        "region": source.region,
        "category": source.category,
        "language": source.language,
        "priority": source.priority,
        "polling_interval_minutes": source.polling_interval_minutes,
        "status": source.status,
        "description": source.description,
        "last_successful_check": source.last_successful_check.isoformat() if source.last_successful_check else None,
        "last_failed_check": source.last_failed_check.isoformat() if source.last_failed_check else None,
        "consecutive_failures": source.consecutive_failures,
        "last_successful_item": source.last_successful_item.isoformat() if source.last_successful_item else None,
        "response_time_ms": source.response_time_ms,
        "total_stories_collected": source.total_stories_collected,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
        "created_by": source.created_by,
    }


@router.get("/{source_id}/health", response_model=dict)
async def get_source_health(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get health history for a specific source
    """
    # Verify source exists
    source_query = select(NewsSource).where(NewsSource.id == source_id)
    source_result = await db.execute(source_query)
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Get recent health history (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    health_query = select(SourceHealthHistory).where(
        SourceHealthHistory.source_id == source_id,
        SourceHealthHistory.checked_at >= thirty_days_ago
    ).order_by(SourceHealthHistory.checked_at.desc())

    health_result = await db.execute(health_query)
    health_records = health_result.scalars().all()

    # Calculate health metrics
    total_checks = len(health_records)
    healthy_checks = sum(1 for h in health_records if h.health_status == "healthy")
    error_checks = sum(1 for h in health_records if h.health_status == "error")
    avg_response_time = sum(h.response_time_ms for h in health_records if h.response_time_ms) / total_checks if total_checks > 0 else 0
    avg_stories_per_check = sum(h.stories_found for h in health_records) / total_checks if total_checks > 0 else 0

    return {
        "source_id": str(source_id),
        "source_name": source.name,
        "current_status": source.status,
        "consecutive_failures": source.consecutive_failures,
        "last_successful_check": source.last_successful_check.isoformat() if source.last_successful_check else None,
        "health_metrics": {
            "total_checks_30_days": total_checks,
            "healthy_checks": healthy_checks,
            "error_checks": error_checks,
            "success_rate": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
            "avg_response_time_ms": round(avg_response_time, 2),
            "avg_stories_per_check": round(avg_stories_per_check, 2),
        },
        "recent_history": [
            {
                "id": str(h.id),
                "health_status": h.health_status,
                "response_time_ms": h.response_time_ms,
                "stories_found": h.stories_found,
                "error_message": h.error_message,
                "checked_at": h.checked_at.isoformat() if h.checked_at else None,
            }
            for h in health_records[:50]  # Last 50 records
        ]
    }


@router.post("/", response_model=dict, status_code=201)
async def create_source(
    source_data: dict,
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new news source (service role required)
    """
    new_source = NewsSource(
        name=source_data.get("name"),
        website_url=source_data.get("website_url"),
        feed_url=source_data.get("feed_url"),
        source_type=source_data.get("source_type", "RSS"),
        country=source_data.get("country", "Global"),
        region=source_data.get("region"),
        category=source_data.get("category", "General"),
        language=source_data.get("language", "en"),
        priority=source_data.get("priority", "medium"),
        polling_interval_minutes=source_data.get("polling_interval_minutes", 15),
        status=source_data.get("status", "active"),
        description=source_data.get("description"),
        created_by=current_user.get("user_id"),
    )

    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)

    return {
        "id": str(new_source.id),
        "name": new_source.name,
        "source_type": new_source.source_type,
        "status": new_source.status,
        "created_at": new_source.created_at.isoformat() if new_source.created_at else None,
    }


@router.put("/{source_id}", response_model=dict)
async def update_source(
    source_id: str,
    source_data: dict,
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing news source (service role required)
    """
    query = select(NewsSource).where(NewsSource.id == source_id)
    result = await db.execute(query)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Update fields
    for field, value in source_data.items():
        if hasattr(source, field) and field not in ["id", "created_at"]:
            setattr(source, field, value)

    await db.commit()
    await db.refresh(source)

    return {
        "id": str(source.id),
        "name": source.name,
        "status": source.status,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
    }


@router.delete("/{source_id}", response_model=dict)
async def delete_source(
    source_id: str,
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (archive) a news source (service role required)
    """
    query = select(NewsSource).where(NewsSource.id == source_id)
    result = await db.execute(query)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Soft delete by archiving
    source.status = "archived"
    await db.commit()

    return {
        "id": str(source.id),
        "status": "archived",
        "message": "Source archived successfully"
    }
