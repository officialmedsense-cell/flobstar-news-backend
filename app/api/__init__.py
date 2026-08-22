"""
API routers for Flobstar News Intelligence
"""

from app.api.sources import router as sources_router
from app.api.stories import router as stories_router
from app.api.assignments import router as assignments_router
from app.api.notifications import router as notifications_router
from app.api.poller import router as poller_router

__all__ = [
    "sources_router",
    "stories_router",
    "assignments_router",
    "notifications_router",
    "poller_router",
]

