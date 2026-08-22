"""
Background task scheduler
Runs the 24/7 source poller at configurable intervals.
On Render free plan, the health endpoint keeps the service alive.
"""

import asyncio
from datetime import datetime, timezone
import structlog

from app.tasks.source_poller import poll_sources
from app.core.config import settings

logger = structlog.get_logger()


class TaskScheduler:
    """Async task scheduler for periodic background jobs."""

    def __init__(self):
        self.running = False
        self._tasks = []

    async def start(self):
        """Start all background tasks."""
        logger.info("Starting Flobstar task scheduler")
        self.running = True

        # Primary: RSS source poller
        self._tasks.append(
            asyncio.create_task(self._run_poller_loop(), name="source-poller")
        )
        logger.info(
            "Background poller scheduled",
            interval_minutes=settings.RSS_POLLING_INTERVAL_MINUTES,
        )

    async def stop(self):
        """Gracefully stop all background tasks."""
        logger.info("Stopping task scheduler")
        self.running = False

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("Task scheduler stopped")

    async def _run_poller_loop(self):
        """
        Run the source poller on a fixed interval.
        Interval is set by RSS_POLLING_INTERVAL_MINUTES in .env (default: 15).
        On Render, UptimeRobot pings /health every 5 min so the service never sleeps.
        """
        interval_seconds = settings.RSS_POLLING_INTERVAL_MINUTES * 60

        # Run immediately on startup
        await self._safe_poll()

        while self.running:
            next_run = datetime.now(timezone.utc).isoformat()
            logger.info(
                f"Poller sleeping {settings.RSS_POLLING_INTERVAL_MINUTES} min until next cycle",
                next_cycle_at=next_run,
            )
            await asyncio.sleep(interval_seconds)
            if self.running:
                await self._safe_poll()

    async def _safe_poll(self):
        """Run poll_sources with error isolation."""
        try:
            await poll_sources()
        except Exception as e:
            logger.error("Uncaught error in poll cycle", error=str(e))

    async def trigger_manual_poll(self):
        """Trigger an immediate out-of-schedule poll (e.g., via API endpoint)."""
        logger.info("Manual poll triggered")
        asyncio.create_task(self._safe_poll(), name="manual-poll")
        return {"triggered": True, "message": "Manual poll started"}


# Global scheduler instance
scheduler = TaskScheduler()
