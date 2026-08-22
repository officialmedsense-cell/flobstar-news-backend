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
    r"(premium|subscriber[\-\s]only|members[\-\s]only)",
    r"(create a free account|sign up to read|log in to read)",
    r"this article is (for|available to) (subscribers|members|premium)",
    r"(you've reached|you have reached) your (free article|monthly limit)",
    r"to (continue|keep) reading",
    r"unlock (this|full) (article|story|content)",
    r"metered paywall",
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
                resp = await client.get(
                    f"{self.base_url}/rest/v1/articles",
                    headers=self.headers,
                    params={
                        "select": "id",
                        "source_url": f"eq.{source_url}",
                        "limit": "1",
                    },
                )
                data = resp.json()
                return isinstance(data, list) and len(data) > 0
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
                data = resp.json()
                if not isinstance(data, list):
                    return False
                for item in data:
                    stored = re.sub(r"[^\w\s]", "", (item.get("title") or "").lower())
                    stored = re.sub(r"\s+", " ", stored).strip()
                    # Simple substring similarity: if normalized is mostly in stored
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
        article_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = {
            "id": article_id,
            "title": title,
            "summary": summary,
            "content": content,
            "category": category,
            "author": author,
            "source_name": source_name,
            "source_url": source_url,
            "status": "draft",
            "image": image_url or "",
            "originalImage": image_url or "",
            # Audit timestamps
            "original_published_at": published_at.isoformat() if published_at else None,
            "detected_at": detected_at.isoformat(),
            "processed_at": processed_at.isoformat(),
            # Metadata
            "source_depth": source_depth,
            "source_word_count": source_word_count,
            "ai_generated": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/rest/v1/articles",
                    headers=self.headers,
                    json=payload,
                )
                if resp.status_code in (200, 201):
                    result = resp.json()
                    inserted_id = (
                        result[0].get("id") if isinstance(result, list) else result.get("id")
                    )
                    logger.info(
                        "Draft article saved to Supabase",
                        id=inserted_id or article_id,
                        title=title[:60],
                        category=category,
                    )
                    return inserted_id or article_id
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
