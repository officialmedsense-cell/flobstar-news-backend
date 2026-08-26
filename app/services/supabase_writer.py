"""
Supabase Writer Service
Writes AI-generated article drafts directly to the Flobstar News Supabase
'articles' table — the same table used by the Next.js frontend newsroom.
"""

import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Paywall detection patterns
# ──────────────────────────────────────────────────────────────────────────────
PAYWALL_PATTERNS = [
    r"subscribe (to|now|for) (read|access|continue)",
    r"(this is a subscriber[\-\s]only|for subscribers[\-\s]only|members[\-\s]only content)",
    r"(create a free account to read|sign up to read full|log in to read full)",
    r"this article is (exclusively for|available only to) (subscribers|members)",
    r"(you've reached|you have reached) your (free article limit|monthly limit)",
    r"(subscribe to continue reading|metered paywall)",
    r"unlock (this|full) (article|story) with a subscription",
    r"\[subscription required\]",
]
_PAYWALL_RE = re.compile("|".join(PAYWALL_PATTERNS), re.IGNORECASE)


def _count_substantive_words(text: str) -> int:
    """Count words longer than 2 characters (filters stop words & noise)."""
    if not text:
        return 0
    words = re.findall(r"\b\w{3,}\b", text)
    return len(words)


def detect_paywall(text: str) -> bool:
    """Return True if the text appears to be blocked by a paywall."""
    return bool(_PAYWALL_RE.search(text or ""))


# ──────────────────────────────────────────────────────────────────────────────
# Source sufficiency thresholds (matching frontend TypeScript constants)
# ──────────────────────────────────────────────────────────────────────────────
SOURCE_FULL_THRESHOLD = 250
SOURCE_PARTIAL_THRESHOLD = 60   # lowered: RSS summaries average 80-150 words combined


def evaluate_source(text: str) -> Dict[str, Any]:
    """
    Classify source depth and detect paywall.

    Returns:
        {
          "depth": "FULL_SOURCE" | "PARTIAL_SOURCE" | "SNIPPET_ONLY",
          "word_count": int,
          "is_paywall": bool,
          "can_generate": bool,
        }
    """
    is_paywall = detect_paywall(text)
    wc = _count_substantive_words(text)

    if is_paywall or wc < SOURCE_PARTIAL_THRESHOLD:
        depth = "SNIPPET_ONLY"
        can_generate = False
    elif wc < SOURCE_FULL_THRESHOLD:
        depth = "PARTIAL_SOURCE"
        can_generate = True
    else:
        depth = "FULL_SOURCE"
        can_generate = True

    return {
        "depth": depth,
        "word_count": wc,
        "is_paywall": is_paywall,
        "can_generate": can_generate,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Supabase REST writer
# ──────────────────────────────────────────────────────────────────────────────

class SupabaseWriter:
    """Writes article drafts directly to the Supabase articles table via REST."""

    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def url_already_stored(self, source_url: str) -> bool:
        """Check if an article with this source URL already exists (dedup gate)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                for table in ["news_stories", "articles"]:
                    col = "original_url" if table == "news_stories" else "source_url"
                    resp = await client.get(
                        f"{self.base_url}/rest/v1/{table}",
                        headers=self.headers,
                        params={
                            "select": "id",
                            col: f"eq.{source_url}",
                            "limit": "1",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            return True
            return False
        except Exception as e:
            logger.error("Supabase dedup check failed", error=str(e))
            return False  # Fail open — let article proceed

    async def headline_already_stored(self, headline: str) -> bool:
        """
        Fuzzy dedup: if a story with the same normalized headline exists in the
        last 48 hours, treat it as a duplicate.
        """
        try:
            # Normalize: lowercase, strip punctuation, collapse spaces
            normalized = re.sub(r"[^\w\s]", "", headline.lower()).strip()
            normalized = re.sub(r"\s+", " ", normalized)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/rest/v1/articles",
                    headers=self.headers,
                    params={
                        "select": "id,title",
                        "status": "neq.archived",
                        "created_at": f"gte.{datetime.now(timezone.utc).isoformat()[:10]}",
                        "limit": "50",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        for item in data:
                            stored = re.sub(r"[^\w\s]", "", (item.get("title") or "").lower())
                            stored = re.sub(r"\s+", " ", stored).strip()
                            words_a = set(normalized.split())
                            words_b = set(stored.split())
                            if words_a and words_b:
                                overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
                                if overlap > 0.75:
                                    return True
            return False
        except Exception as e:
            logger.error("Supabase headline dedup check failed", error=str(e))
            return False

    async def write_draft(
        self,
        *,
        title: str,
        summary: str,
        content: str,
        category: str,
        author: str,
        source_name: str,
        source_url: str,
        published_at: Optional[datetime],
        detected_at: datetime,
        processed_at: datetime,
        image_url: Optional[str] = None,
        source_depth: str = "FULL_SOURCE",
        source_word_count: int = 0,
    ) -> Optional[str]:
        """
        Insert an AI-generated article draft into the Supabase articles table.
        Returns the new article ID on success, None on failure.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        random_suffix = uuid.uuid4().hex[:6]
        clean_slug = re.sub(r"[^\w\s-]", "", title.lower()).strip().replace(" ", "-")[:70]
        slug = f"{clean_slug}-{random_suffix}" if clean_slug else f"story-{random_suffix}"

        # Exact schema payload for Supabase 'articles' table
        article_payload = {
            "title": title,
            "excerpt": summary,
            "content": content,
            "category": category or "Health",
            "author": author or "Flobstar News",
            "status": "draft",
            "image": image_url or "",
            "source_url": source_url or "",
            "slug": slug,
            "date": now_iso[:10],
            "created_at": now_iso,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/rest/v1/articles",
                    headers=self.headers,
                    json=article_payload,
                )
                if resp.status_code in (200, 201):
                    result = resp.json()
                    inserted_id = str(result[0].get("id")) if isinstance(result, list) and result else None
                    logger.info(
                        "Draft article saved to Supabase",
                        id=inserted_id,
                        title=title[:60],
                        category=category,
                    )
                    return inserted_id
                else:
                    logger.error(
                        "Supabase write_draft failed",
                        status=resp.status_code,
                        body=resp.text[:300],
                    )
                    return None
        except Exception as e:
            logger.error("Supabase write_draft exception", error=str(e))
            return None


# Global instance
supabase_writer = SupabaseWriter()
