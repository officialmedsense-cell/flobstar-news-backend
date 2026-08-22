"""
Flobstar News — 24/7 Source Poller
====================================
Core background task that runs continuously on Render to:
  1. Fetch all active RSS feeds in parallel (async, 8-second timeout each)
  2. Apply the 1-hour freshness gate (articles older than 24 hours are skipped)
  3. Deduplicate by URL first, then by headline similarity
  4. Acquire full article text via web scraper (httpx + BeautifulSoup)
  5. Evaluate source depth (FULL / PARTIAL / SNIPPET_ONLY)
  6. Hard-stop if source is paywalled or word count < 80
  7. AI-generate a Flobstar-standard article (Mistral primary)
  8. Save the draft directly to Supabase articles table
  9. Fire Telegram newsroom alert with one-click review link
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import httpx
import feedparser
import structlog

from app.core.config import settings
from app.services.supabase_writer import supabase_writer, evaluate_source
from app.services.ai_generator import ai_generator
from app.services.rss_parser import RSSParser
from app.services.web_scraper import WebScraper
from app.services.flobstar_system_prompt import normalize_rss_category
from app.notifications.telegram import telegram

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Freshness configuration
# ──────────────────────────────────────────────────────────────────────────────
PRIORITY_WINDOW_HOURS = 1      # Must cover: articles in the last 1 hour
MAX_ARTICLE_AGE_HOURS = 24     # Upper bound: skip articles older than 24 hours

# ──────────────────────────────────────────────────────────────────────────────
# Default open-access RSS feed list (curated, verified 2025)
# Staff can override these via the Supabase news_sources table.
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_FEEDS: List[Dict[str, str]] = [
    # ── GLOBAL PUBLIC HEALTH ─────────────────────────────────────────────────
    {"name": "WHO News",                   "url": "https://www.who.int/rss-feeds/news-english.xml",            "category": "Public Health"},
    {"name": "CDC Newsroom",               "url": "https://tools.cdc.gov/api/v2/resources/media/404952.rss",   "category": "Public Health"},
    {"name": "Healthline",                 "url": "https://www.healthline.com/rss/news",                       "category": "Health"},
    {"name": "Medical News Today",         "url": "https://www.medicalnewstoday.com/rss/medicalnewstoday.xml", "category": "Health"},
    {"name": "WebMD Health News",          "url": "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC_NEWS", "category": "Health"},
    {"name": "Reuters Health",             "url": "https://feeds.reuters.com/reuters/healthNews",              "category": "Medicine"},
    {"name": "AP Health",                  "url": "https://feeds.apnews.com/rss/apf-Health",                  "category": "Health"},
    {"name": "BBC Health",                 "url": "https://feeds.bbci.co.uk/news/health/rss.xml",             "category": "Health"},
    {"name": "The Lancet",                 "url": "https://www.thelancet.com/rssfeed/lancet_online.xml",      "category": "Research"},
    {"name": "NEJM",                       "url": "https://www.nejm.org/action/showFeed?jc=nejmoa&type=etoc&feed=rss", "category": "Research"},
    {"name": "Nature Medicine",            "url": "https://www.nature.com/nm.rss",                            "category": "Research"},
    {"name": "BMJ",                        "url": "https://www.bmj.com/rss/current.xml",                      "category": "Research"},
    {"name": "Science Daily Health",       "url": "https://www.sciencedaily.com/rss/health_medicine.xml",     "category": "Research"},
    {"name": "PubMed Latest",              "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1q2W3kJ1bDj7u8pGPpJAXCCnHNNmgALz5NAhLQfT_/",
                                                                                                               "category": "Research"},
    {"name": "JAMA",                       "url": "https://jamanetwork.com/rss/site_3/67.xml",                "category": "Medicine"},
    # ── PHARMACEUTICAL & BIOTECH ─────────────────────────────────────────────
    {"name": "FDA News",                   "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/fda-news-releases/rss.xml", "category": "Pharmaceutical"},
    {"name": "BioPharma Dive",             "url": "https://www.biopharmadive.com/feeds/news/",                "category": "Pharmaceutical"},
    {"name": "FiercePharma",               "url": "https://www.fiercepharma.com/rss/xml",                    "category": "Pharmaceutical"},
    {"name": "Endpoints News",             "url": "https://endpts.com/feed/",                                 "category": "Pharmaceutical"},
    # ── HEALTH TECHNOLOGY ────────────────────────────────────────────────────
    {"name": "MobiHealthNews",             "url": "https://www.mobihealthnews.com/rss.xml",                   "category": "Technology"},
    {"name": "Health IT Analytics",        "url": "https://healthitanalytics.com/feed/",                     "category": "Technology"},
    {"name": "Digital Health Today",       "url": "https://digitalhealthtoday.com/feed/",                    "category": "Technology"},
    {"name": "Health Data Management",     "url": "https://www.healthdatamanagement.com/feed",               "category": "Technology"},
    # ── MENTAL HEALTH ────────────────────────────────────────────────────────
    {"name": "Psychology Today",           "url": "https://www.psychologytoday.com/intl/front-page/feed",    "category": "Mental Health"},
    {"name": "Mind.org.uk",                "url": "https://www.mind.org.uk/information-support/rss/",        "category": "Mental Health"},
    # ── ENVIRONMENT & CLIMATE ────────────────────────────────────────────────
    {"name": "Environmental Health News",  "url": "https://www.ehn.org/feed/",                               "category": "Environment & Climate"},
    {"name": "The Guardian Environment",   "url": "https://www.theguardian.com/environment/rss",             "category": "Environment & Climate"},
    # ── AFRICA & NIGERIA ─────────────────────────────────────────────────────
    {"name": "Africa CDC",                 "url": "https://africacdc.org/feed/",                             "category": "Public Health"},
    {"name": "The Guardian Nigeria",       "url": "https://guardian.ng/category/features/health/feed/",      "category": "Public Health"},
    {"name": "Vanguard Nigeria Health",    "url": "https://www.vanguardngr.com/category/health/feed/",       "category": "Public Health"},
    {"name": "Punch Nigeria Health",       "url": "https://punchng.com/category/health/feed/",               "category": "Public Health"},
    {"name": "Channels TV Health",         "url": "https://www.channelstv.com/category/health/feed/",        "category": "Public Health"},
    {"name": "The Nation Nigeria Health",  "url": "https://thenationonlineng.net/category/health/feed/",     "category": "Public Health"},
    {"name": "Premium Times Health",       "url": "https://www.premiumtimesng.com/health/feed",              "category": "Public Health"},
    {"name": "THISDAY Health",             "url": "https://www.thisdaylive.com/index.php/category/health/feed/", "category": "Public Health"},
    {"name": "AllAfrica Health",           "url": "https://allafrica.com/health/rss2.0.xml",                 "category": "Public Health"},
    {"name": "Devex Global Health",        "url": "https://www.devex.com/news/rss/health",                   "category": "Global Health"},
    {"name": "Health Policy Watch",        "url": "https://healthpolicy-watch.news/feed/",                   "category": "Health Policy"},
    {"name": "Impatient Health",           "url": "https://www.impatica.io/feed/",                           "category": "Health Policy"},
    # ── HEALTH BUSINESS ──────────────────────────────────────────────────────
    {"name": "Healthcare Finance News",    "url": "https://www.healthcarefinancenews.com/rss.xml",           "category": "Health Business"},
    {"name": "Modern Healthcare",          "url": "https://www.modernhealthcare.com/rss/news",               "category": "Health Business"},
]


# ──────────────────────────────────────────────────────────────────────────────
# Active feed list — load from Supabase news_sources if available, else DEFAULT
# ──────────────────────────────────────────────────────────────────────────────

async def load_active_feeds() -> List[Dict[str, str]]:
    """
    Try to load active RSS sources from the Supabase news_sources table.
    Falls back to DEFAULT_FEEDS if the table is empty or unreachable.
    """
    try:
        url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/news_sources"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }
        params = {"select": "name,feed_url,category", "status": "eq.active"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers, params=params)
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                feeds = [
                    {
                        "name": row.get("name", "Unknown"),
                        "url": row.get("feed_url", ""),
                        "category": row.get("category") or "Health",
                    }
                    for row in data
                    if row.get("feed_url")
                ]
                if feeds:
                    logger.info(f"Loaded {len(feeds)} active feeds from Supabase news_sources")
                    return feeds
    except Exception as e:
        logger.warning("Could not load feeds from Supabase — using defaults", error=str(e))

    logger.info(f"Using {len(DEFAULT_FEEDS)} default RSS feeds")
    return DEFAULT_FEEDS


# ──────────────────────────────────────────────────────────────────────────────
# Per-entry freshness check
# ──────────────────────────────────────────────────────────────────────────────

def is_fresh(published_at: Optional[datetime]) -> bool:
    """
    Return True if the article is fresh enough to process.
    Articles older than MAX_ARTICLE_AGE_HOURS are skipped entirely.
    """
    if published_at is None:
        # If no publish date is available, treat as potentially fresh
        return True
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age = now - published_at
    return age <= timedelta(hours=MAX_ARTICLE_AGE_HOURS)


def is_priority_fresh(published_at: Optional[datetime]) -> bool:
    """Return True if the article was published in the last 1 hour (priority)."""
    if published_at is None:
        return False
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return (now - published_at) <= timedelta(hours=PRIORITY_WINDOW_HOURS)


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, text/html, application/xhtml+xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ──────────────────────────────────────────────────────────────────────────────
# Single feed poller with concurrency limiting
# ──────────────────────────────────────────────────────────────────────────────

async def _poll_one_feed(feed: Dict[str, str], sem: asyncio.Semaphore) -> List[Dict[str, Any]]:
    """
    Fetch and parse one RSS feed safely using a concurrency semaphore.
    """
    name = feed["name"]
    url = feed["url"]
    default_category = feed.get("category", "Health")

    async with sem:
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.debug(f"[{name}] HTTP status {resp.status_code}")
                    return []
                raw = resp.content

            parsed = feedparser.parse(raw)
            entries = []

            for entry in parsed.entries:
                pub = entry.get("published_parsed")
                published_at = datetime(*pub[:6], tzinfo=timezone.utc) if pub else None

                # Freshness gate — skip old articles immediately
                if not is_fresh(published_at):
                    continue

                # Extract content
                content = ""
                if hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", "")
                if not content:
                    content = getattr(entry, "summary", "") or ""

                # Extract tags for category normalization
                tags = [tag.get("term", "") for tag in getattr(entry, "tags", [])]
                raw_cat = tags[0] if tags else default_category
                category = normalize_rss_category(raw_cat) or default_category

                entries.append({
                    "source_name": name,
                    "source_url": entry.get("link", ""),
                    "title": entry.get("title", "").strip(),
                    "summary": getattr(entry, "summary", "").strip(),
                    "rss_content": content.strip(),
                    "published_at": published_at,
                    "detected_at": datetime.now(timezone.utc),
                    "category": category,
                    "is_priority": is_priority_fresh(published_at),
                })

            if entries:
                logger.info(f"[{name}] {len(entries)} fresh entries found")
            return entries

        except Exception as e:
            logger.debug(f"[{name}] Feed skip: {e}")
            return []


# ──────────────────────────────────────────────────────────────────────────────
# Full-text acquisition via web scraper
# ──────────────────────────────────────────────────────────────────────────────

async def _acquire_full_text(url: str, rss_content: str) -> str:
    """
    Attempt to scrape full article text from the original URL.
    Falls back to the RSS content if scraping fails or returns less content.
    """
    try:
        async with WebScraper(timeout=15) as scraper:
            data = await scraper.scrape_article(url)
            scraped = data.get("content", "")
            if scraped and len(scraped) > len(rss_content):
                return scraped
    except Exception as e:
        logger.debug(f"Scrape fallback for {url}: {e}")

    return rss_content


# ──────────────────────────────────────────────────────────────────────────────
# Main polling task
# ──────────────────────────────────────────────────────────────────────────────

async def poll_sources():
    """
    Main 24/7 polling task — called by the scheduler every 15 minutes.

    Flow:
      1. Load active RSS feeds from Supabase (or defaults)
      2. Fetch all feeds in parallel
      3. Sort entries: priority (< 1 hr) first, then recency
      4. For each unique entry:
         a. URL dedup check against Supabase
         b. Headline dedup check
         c. Acquire full text (scraper → RSS fallback)
         d. Source sufficiency + paywall gate
         e. AI generate full Flobstar article
         f. Save draft to Supabase articles table
         g. Telegram newsroom alert with direct review link
    """
    poll_start = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("Flobstar 24/7 Source Poller — cycle start", time=poll_start.isoformat())

    # 1. Load active feeds
    feeds = await load_active_feeds()

    # 2. Fetch all feeds in parallel with controlled concurrency (5 at a time)
    sem = asyncio.Semaphore(5)
    tasks = [_poll_one_feed(feed, sem) for feed in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_entries: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, list):
            all_entries.extend(r)

    logger.info(f"Total fresh RSS entries collected: {len(all_entries)}")

    # 3. Sort: priority (< 1 hr) first, then newest-first
    all_entries.sort(key=lambda e: (
        0 if e["is_priority"] else 1,
        -(e["published_at"].timestamp() if e["published_at"] else 0)
    ))

    # Metrics
    stats = {
        "seen": len(all_entries),
        "skipped_dedup": 0,
        "skipped_insufficient": 0,
        "skipped_ai_fail": 0,
        "drafts_saved": 0,
    }

    # 4. Process each entry
    for entry in all_entries:
        source_url = entry["source_url"]
        title = entry["title"]

        if not source_url or not title:
            continue

        # ── a. URL dedup ──────────────────────────────────────────────
        if await supabase_writer.url_already_stored(source_url):
            stats["skipped_dedup"] += 1
            logger.debug(f"[DEDUP:URL] {title[:50]}")
            continue

        # ── b. Headline dedup ─────────────────────────────────────────
        if await supabase_writer.headline_already_stored(title):
            stats["skipped_dedup"] += 1
            logger.debug(f"[DEDUP:HEADLINE] {title[:50]}")
            continue

        # ── c. Full-text acquisition ──────────────────────────────────
        logger.info(f"Acquiring full text: {title[:60]}")
        full_text = await _acquire_full_text(source_url, entry["rss_content"])

        # ── d. Source sufficiency gate ────────────────────────────────
        evaluation = evaluate_source(full_text)

        if not evaluation["can_generate"]:
            reason = "PAYWALLED" if evaluation["is_paywall"] else "SNIPPET_ONLY"
            logger.info(
                f"[HARD STOP: {reason}] {title[:60]} "
                f"(words: {evaluation['word_count']})"
            )
            stats["skipped_insufficient"] += 1
            continue

        logger.info(
            f"Source depth: {evaluation['depth']} "
            f"({evaluation['word_count']} words) — generating article"
        )

        # ── e. AI generation ──────────────────────────────────────────
        processed_at = datetime.now(timezone.utc)

        try:
            # Generate Flobstar headline
            flobstar_headline = await ai_generator.generate_headline(
                original_headline=title,
                original_content=full_text[:3000],
            )

            # Generate lead summary
            flobstar_summary = await ai_generator.generate_summary(
                original_content=full_text[:3000],
                max_length=200,
            )

            # Generate full article body
            flobstar_article = await ai_generator.generate_full_article(
                original_headline=flobstar_headline,
                original_content=full_text[:8000],
                category=entry["category"],
            )

            if not flobstar_article or len(flobstar_article.strip()) < 100:
                logger.warning(f"AI returned empty/short article for: {title[:50]}")
                stats["skipped_ai_fail"] += 1
                continue

        except Exception as e:
            logger.error(f"AI generation failed for: {title[:50]}", error=str(e))
            stats["skipped_ai_fail"] += 1
            continue

        # ── f. Save draft to Supabase ─────────────────────────────────
        article_id = await supabase_writer.write_draft(
            title=flobstar_headline,
            summary=flobstar_summary,
            content=flobstar_article,
            category=entry["category"],
            author="Flobstar AI",
            source_name=entry["source_name"],
            source_url=source_url,
            published_at=entry["published_at"],
            detected_at=entry["detected_at"],
            processed_at=processed_at,
            source_depth=evaluation["depth"],
            source_word_count=evaluation["word_count"],
        )

        if not article_id:
            stats["skipped_ai_fail"] += 1
            continue

        stats["drafts_saved"] += 1
        priority_flag = "🚨 BREAKING" if entry["is_priority"] else "📰 NEW DRAFT"
        logger.info(
            f"{priority_flag} saved: {flobstar_headline[:70]} "
            f"[{entry['category']}] id={article_id}"
        )

        # ── g. Telegram newsroom alert ────────────────────────────────
        await telegram.alert_new_draft(
            headline=flobstar_headline,
            category=entry["category"],
            source_name=entry["source_name"],
            article_id=article_id,
            is_breaking=entry["is_priority"],
        )

        # Small delay between articles to avoid rate-limiting AI APIs
        await asyncio.sleep(1.5)

    # Cycle complete summary
    elapsed = (datetime.now(timezone.utc) - poll_start).total_seconds()
    logger.info(
        "Poll cycle complete",
        elapsed_seconds=round(elapsed, 1),
        seen=stats["seen"],
        deduped=stats["skipped_dedup"],
        insufficient=stats["skipped_insufficient"],
        ai_fail=stats["skipped_ai_fail"],
        drafts_saved=stats["drafts_saved"],
    )

    # Periodic summary to Telegram (only when something was saved)
    if stats["drafts_saved"] > 0:
        await telegram.alert_poll_summary(
            drafts_saved=stats["drafts_saved"],
            seen=stats["seen"],
            elapsed=round(elapsed, 1),
        )
