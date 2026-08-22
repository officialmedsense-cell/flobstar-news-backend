"""
Background tasks for Flobstar News Intelligence
"""

from app.tasks.source_poller import poll_sources

__all__ = [
    "poll_sources",
]
