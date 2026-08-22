"""
API endpoints for news sources (Powered by high-speed Supabase REST)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import structlog

from app.core.supabase_client import supabase_client
from app.tasks.source_poller import DEFAULT_FEEDS

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=List[dict])
@router.get("/", response_model=List[dict])
async def list_sources(
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List news sources with optional filtering."""
    params: Dict[str, Any] = {
        "select": "*",
        "order": "created_at.desc",
        "offset": str(skip),
        "limit": str(limit),
    }
    if status and status != "all":
        params["status"] = f"eq.{status}"
    if category and category != "all":
        params["category"] = f"eq.{category}"

    sources = await supabase_client.get("news_sources", params)
    
    # If Supabase news_sources is empty, return formatted DEFAULT_FEEDS
    if not sources:
        return [
            {
                "id": str(idx),
                "name": f["name"],
                "website_url": f["url"],
                "feed_url": f["url"],
                "category": f.get("category", "Health"),
                "status": "active",
                "priority": "routine",
                "consecutive_failures": 0,
                "total_stories_collected": 0,
            }
            for idx, f in enumerate(DEFAULT_FEEDS, 1)
        ]

    return sources


@router.get("/{source_id}", response_model=dict)
async def get_source(source_id: str):
    """Get a specific news source by ID."""
    source = await supabase_client.get_by_id("news_sources", source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("", response_model=dict, status_code=201)
@router.post("/", response_model=dict, status_code=201)
async def create_source(source_data: dict):
    """Create a new news source."""
    if "id" not in source_data:
        source_data["id"] = str(uuid.uuid4())
    if "created_at" not in source_data:
        source_data["created_at"] = datetime.now(timezone.utc).isoformat()
    if "status" not in source_data:
        source_data["status"] = "active"

    created = await supabase_client.insert("news_sources", source_data)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create source")
    return created


@router.put("/{source_id}", response_model=dict)
async def update_source(source_id: str, source_data: dict):
    """Update a news source."""
    source_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated = await supabase_client.update("news_sources", source_id, source_data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update source")
    return updated


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    """Delete a news source."""
    success = await supabase_client.delete("news_sources", source_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete source")
    return {"message": "Source deleted successfully"}
