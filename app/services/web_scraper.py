"""
Web Scraper Service
"""

from bs4 import BeautifulSoup
import httpx
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()

# Cap scraped text to avoid holding large DOM text in RAM
MAX_SCRAPE_CHARS = 8_000


class WebScraper:
    """Service for scraping web pages for news content."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def scrape_article(self, url: str) -> Dict:
        """
        Scrape a news article from a URL.
        Uses a short-lived per-request client to avoid connection accumulation.

        Returns:
            Dictionary containing article data
        """
        soup = None
        try:
            logger.info("Scraping article", url=url)

            # Use a fresh client per request — avoids connection pool memory accumulation
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                raw_html = response.content

            # Parse HTML — lxml is fast and memory-efficient
            soup = BeautifulSoup(raw_html, "lxml")
            del raw_html  # Release raw bytes immediately

            # Extract article data
            article_data = {
                "title": self._extract_title(soup),
                "content": self._extract_content(soup),
                "author": self._extract_author(soup),
                "published_date": self._extract_date(soup),
                "description": self._extract_description(soup),
                "url": url,
            }

            logger.info("Successfully scraped article", url=url, title=article_data["title"])

            return article_data

        except httpx.HTTPError as e:
            logger.error("HTTP error scraping article", url=url, error=str(e))
            raise
        except Exception as e:
            logger.error("Error scraping article", url=url, error=str(e))
            raise
        finally:
            # Always decompose the BeautifulSoup tree to release the DOM from RAM
            if soup is not None:
                try:
                    soup.decompose()
                except Exception:
                    pass

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title from HTML"""
        # Try common title selectors
        selectors = [
            "h1",
            ".article-title",
            ".post-title",
            ".entry-title",
            "[property='og:title']",
            "title",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 10:  # Filter out short/invalid titles
                    return title

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract article content from HTML, capped at MAX_SCRAPE_CHARS."""
        # Try common content selectors
        selectors = [
            "article",
            ".article-content",
            ".post-content",
            ".entry-content",
            ".content",
            "main",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Remove unwanted elements
                for unwanted in element.select("script, style, nav, footer, aside, .ads, .advertisement"):
                    unwanted.decompose()

                content = element.get_text(separator="\n", strip=True)
                if content and len(content) > 100:  # Filter out short content
                    # Cap output to avoid large string allocations
                    return content[:MAX_SCRAPE_CHARS]

        return ""

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract article author from HTML"""
        selectors = [
            ".author",
            ".post-author",
            ".entry-author",
            "[property='article:author']",
            ".byline",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True)
                if author:
                    return author

        return ""

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from HTML"""
        selectors = [
            "[property='article:published_time']",
            "[property='og:article:published_time']",
            "time[datetime]",
            ".published-date",
            ".post-date",
            ".entry-date",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Try to get datetime attribute first
                date = element.get("datetime") or element.get("content")
                if date:
                    return date
                # Fallback to text content
                date = element.get_text(strip=True)
                if date:
                    return date

        return None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract article description/summary from HTML"""
        selectors = [
            "[property='og:description']",
            "[name='description']",
            ".article-summary",
            ".post-summary",
            ".excerpt",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                desc = element.get("content") or element.get_text(strip=True)
                if desc:
                    return desc

        return ""

    async def close(self):
        """No-op: clients are now per-request and self-closing."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
