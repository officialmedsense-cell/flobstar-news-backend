"""
Poller API — manual trigger, live metrics, and status check.
"""

from fastapi import APIRouter, BackgroundTasks
from datetime import datetime, timezone

router = APIRouter()

# In-memory metrics (reset on restart)
_metrics = {
    "last_poll_at": None,
    "total_drafts_saved": 0,
    "total_articles_seen": 0,
    "poll_cycles": 0,
}


@router.get("/status")
async def poller_status():
    """Return live poller metrics and status."""
    from app.scheduler import scheduler
    from app.notifications.telegram import telegram

    return {
        "poller_running": scheduler.running,
        "telegram_enabled": telegram.enabled,
        "last_poll_at": _metrics["last_poll_at"],
        "poll_cycles": _metrics["poll_cycles"],
        "total_drafts_saved": _metrics["total_drafts_saved"],
        "total_articles_seen": _metrics["total_articles_seen"],
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/trigger")
async def trigger_poll(background_tasks: BackgroundTasks):
    """
    Manually trigger an immediate poll cycle.
    Useful for testing without waiting for the scheduler interval.
    """
    from app.scheduler import scheduler
    result = await scheduler.trigger_manual_poll()
    return result


@router.get("/feeds")
async def list_feeds():
    """Return the current list of active RSS feeds that will be polled."""
    from app.tasks.source_poller import load_active_feeds
    feeds = await load_active_feeds()
    return {"count": len(feeds), "feeds": feeds}


@router.post("/test-telegram")
async def test_telegram_connection():
    """Test the Telegram bot connection and return bot info."""
    from app.notifications.telegram import telegram
    result = await telegram.test_connection()
    return result
