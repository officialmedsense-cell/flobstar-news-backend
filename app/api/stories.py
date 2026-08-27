"""
API endpoints for news stories (Powered by high-speed Supabase REST)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import structlog

from app.core.supabase_client import supabase_client

logger = structlog.get_logger()
router = APIRouter()


def _map_story(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Supabase article/story fields to Newsroom schema."""
    return {
        "id": str(item.get("id")),
        "source_id": item.get("source_id"),
        "source_name": item.get("source_name") or item.get("source") or "News Source",
        "original_url": item.get("source_url") or item.get("original_url") or "",
        "original_headline": item.get("original_title") or item.get("title") or "Headline",
        "flobstar_headline": item.get("title") or item.get("flobstar_headline") or "Headline",
        "flobstar_summary": item.get("summary") or item.get("flobstar_summary") or "",
        "flobstar_content": item.get("content") or item.get("flobstar_content") or "",
        "category": item.get("category") or "Health",
        "priority": item.get("priority") or "routine",
        "status": item.get("status") or "ready",
        "ai_generated": item.get("ai_generated", True),
        "detected_at": item.get("detected_at") or item.get("created_at"),
        "processed_at": item.get("processed_at") or item.get("updated_at"),
        "original_published_at": item.get("original_published_at") or item.get("published_at"),
        "published_at_flobstar": item.get("created_at") if item.get("status") == "published" else None,
        "image": item.get("image") or item.get("originalImage") or "",
        "original_image": item.get("originalImage") or item.get("image") or "",
    }


@router.get("", response_model=List[dict])
@router.get("/", response_model=List[dict])
async def list_stories(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List news stories with optional filtering."""
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
    if priority and priority != "all":
        params["priority"] = f"eq.{priority}"

    # Try articles table first
    items = await supabase_client.get("articles", params)
    
    # If no articles, try news_stories table
    if not items:
        items = await supabase_client.get("news_stories", params)

    return [_map_story(item) for item in items]


@router.get("/stats/dashboard", response_model=dict)
async def get_dashboard_stats():
    """Aggregate real-time editorial stats from Supabase."""
    from app.tasks.source_poller import DEFAULT_FEEDS

    today_iso = datetime.now(timezone.utc).isoformat()[:10]
    
    # Query articles from Supabase
    articles = await supabase_client.get("articles", {
        "select": "id,title,category,status,date,created_at,source_url,image",
        "order": "created_at.desc",
        "limit": "500",
    })
    
    # Query sources from Supabase (or fallback to defaults count)
    sources = await supabase_client.get("news_sources", {"select": "id,status,consecutive_failures"})
    total_sources = len(sources) if sources else len(DEFAULT_FEEDS)
    active_sources = len([s for s in sources if s.get("status") == "active"]) if sources else len(DEFAULT_FEEDS)
    warning_sources = len([s for s in sources if 0 < s.get("consecutive_failures", 0) <= 5]) if sources else 0
    error_sources = len([s for s in sources if s.get("consecutive_failures", 0) > 5]) if sources else 0

    total_scraped = len(articles)
    drafts = [a for a in articles if a.get("status") == "draft"]
    under_review = [a for a in articles if a.get("status") == "under_review"]
    published = [a for a in articles if a.get("status") == "published"]
    published_today = [
        a for a in published
        if (a.get("date") or "")[:10] == today_iso or (a.get("created_at") or "")[:10] == today_iso
    ]
    breaking = [
        a for a in articles
        if a.get("category") == "Health Alert" or a.get("priority") == "breaking"
    ]

    return {
        "stats": {
            "total_scraped": total_scraped,
            "breaking": len(breaking),
            "important": len([a for a in articles if a.get("priority") == "important"]),
            "newStories": len(drafts),
            "assignedToMe": 0,
            "awaitingReview": len(under_review),
            "publishedToday": len(published_today),
            "totalPublished": len(published),
        },
        "sourceHealth": {
            "total": total_sources,
            "active": active_sources,
            "warnings": warning_sources,
            "errors": error_sources,
        },
        "recentStories": [_map_story(a) for a in articles[:10]],
    }


@router.get("/{story_id}", response_model=dict)
async def get_story(story_id: str):
    """Get a specific news story by ID."""
    story = await supabase_client.get_by_id("articles", story_id)
    if not story:
        story = await supabase_client.get_by_id("news_stories", story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return _map_story(story)


@router.post("", response_model=dict, status_code=201)
@router.post("/", response_model=dict, status_code=201)
async def create_story(story_data: dict):
    """Create a new story draft."""
    if "id" not in story_data:
        story_data["id"] = str(uuid.uuid4())
    if "created_at" not in story_data:
        story_data["created_at"] = datetime.now(timezone.utc).isoformat()
    if "status" not in story_data:
        story_data["status"] = "draft"

    created = await supabase_client.insert("articles", story_data)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create story")
    return _map_story(created)


@router.put("/{story_id}", response_model=dict)
async def update_story(story_id: str, story_data: dict):
    """Update a story's headline, summary/excerpt, content, category, or image."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload: Dict[str, Any] = {"updated_at": now_iso}
    
    if "flobstar_headline" in story_data or "title" in story_data:
        payload["title"] = story_data.get("flobstar_headline") or story_data.get("title")
    
    # Supabase 'articles' table uses 'excerpt' for summary/lead
    summary_val = (
        story_data.get("flobstar_summary")
        or story_data.get("summary")
        or story_data.get("excerpt")
    )
    if summary_val is not None:
        payload["excerpt"] = summary_val

    if "flobstar_content" in story_data or "content" in story_data:
        payload["content"] = story_data.get("flobstar_content") or story_data.get("content")
    if "category" in story_data:
        payload["category"] = story_data["category"]
    if "status" in story_data:
        payload["status"] = story_data["status"]
        if story_data["status"] == "published":
            payload["date"] = now_iso[:10]
    if "image" in story_data:
        payload["image"] = story_data["image"]

    updated = await supabase_client.update("articles", story_id, payload)
    if not updated:
        # Fallback to news_stories table (which uses 'summary')
        news_story_payload = {**story_data}
        if "excerpt" in news_story_payload and "summary" not in news_story_payload:
            news_story_payload["summary"] = news_story_payload.pop("excerpt")
        updated = await supabase_client.update("news_stories", story_id, news_story_payload)

    if not updated:
        return {"id": story_id, **story_data}

    return _map_story(updated)


@router.patch("/{story_id}/status", response_model=dict)
async def update_story_status(story_id: str, payload: dict):
    """Update story editorial status (e.g. published, under_review, draft)."""
    new_status = payload.get("status", "draft")
    update_data = {
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    updated = await supabase_client.update("articles", story_id, update_data)
    if not updated:
        updated = await supabase_client.update("news_stories", story_id, {"status": new_status})
    return {"id": story_id, "status": new_status, "success": True}


@router.delete("/{story_id}")
async def delete_story(story_id: str):
    """Delete or archive a story."""
    success = await supabase_client.delete("articles", story_id)
    if not success:
        success = await supabase_client.delete("news_stories", story_id)
    return {"message": "Story deleted successfully", "success": success}
