"""
RSS Feed Parser Service
"""

import feedparser
import httpx
from typing import List, Dict, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class RSSParser:
    """Service for parsing RSS and Atom feeds"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def parse_feed(self, feed_url: str) -> Dict:
        """
        Parse an RSS or Atom feed and return structured data

        Args:
            feed_url: URL of the RSS/Atom feed

        Returns:
            Dictionary containing feed metadata and entries
        """
        try:
            logger.info("Parsing RSS feed", feed_url=feed_url)

            # Fetch the feed
            response = await self.client.get(feed_url)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            # Extract feed metadata
            feed_data = {
                "title": feed.feed.get("title", "Unknown"),
                "description": feed.feed.get("description", ""),
                "link": feed.feed.get("link", ""),
                "language": feed.feed.get("language", "en"),
                "updated": feed.feed.get("updated"),
                "entries": [],
            }

            # Extract entries
            for entry in feed.entries:
                entry_data = self._parse_entry(entry)
                feed_data["entries"].append(entry_data)

            logger.info(
                "Successfully parsed RSS feed",
                feed_url=feed_url,
                entry_count=len(feed_data["entries"])
            )

            return feed_data

        except httpx.HTTPError as e:
            logger.error("HTTP error fetching RSS feed", feed_url=feed_url, error=str(e))
            raise
        except Exception as e:
            logger.error("Error parsing RSS feed", feed_url=feed_url, error=str(e))
            raise

    def _parse_entry(self, entry: Dict) -> Dict:
        """
        Parse a single feed entry

        Args:
            entry: Feedparser entry object

        Returns:
            Dictionary with structured entry data
        """
        # Get published date
        published = entry.get("published_parsed")
        if published:
            published_dt = datetime(*published[:6])
        else:
            published_dt = None

        # Get content
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary

        # Get author
        author = ""
        if hasattr(entry, "author"):
            author = entry.author
        elif hasattr(entry, "author_detail"):
            author = entry.author_detail.get("name", "")

        return {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", ""),
            "content": content,
            "author": author,
            "published": published_dt,
            "tags": [tag.get("term") for tag in entry.get("tags", [])],
            "id": entry.get("id", entry.get("link", "")),
        }

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
