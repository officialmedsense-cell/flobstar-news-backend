"""
Telegram notification service for Flobstar News Intelligence.
Sends breaking news alerts, AI draft notifications, and system updates
to the Flobstar newsroom Telegram channel/group.

All alerts include a direct one-click link to the inline article editor
in the MedSense Dashboard newsroom.
"""

import httpx
import structlog
from typing import Optional
from app.core.config import settings

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier:
    """Sends notifications via Telegram Bot API."""

    def __init__(self):
        self.enabled = bool(
            settings.TELEGRAM_BOT_TOKEN
            and settings.TELEGRAM_CHAT_ID
            and not settings.TELEGRAM_BOT_TOKEN.startswith("your_")
        )
        if self.enabled:
            logger.info(
                "Telegram notifier initialized",
                chat_id=settings.TELEGRAM_CHAT_ID
            )
        else:
            logger.warning("Telegram notifier disabled — BOT_TOKEN or CHAT_ID not configured")

    def _url(self, method: str) -> str:
        return TELEGRAM_API_BASE.format(
            token=settings.TELEGRAM_BOT_TOKEN,
            method=method
        )

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
    ) -> bool:
        """
        Send a message to Telegram.

        Args:
            text: Message content (HTML formatting supported)
            chat_id: Override the default chat ID
            parse_mode: 'HTML' or 'Markdown'
            disable_preview: Disable link previews

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram send skipped — notifier disabled")
            return False

        target_chat = chat_id or settings.TELEGRAM_CHAT_ID

        payload = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self._url("sendMessage"), json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    logger.info("Telegram message sent", chat_id=target_chat)
                    return True
                else:
                    logger.error(
                        "Telegram API returned not-ok",
                        description=data.get("description"),
                    )
                    return False
        except httpx.HTTPError as e:
            logger.error("Telegram HTTP error", error=str(e))
            return False
        except Exception as e:
            logger.error("Telegram unexpected error", error=str(e))
            return False

    # ─────────────────────────────────────────
    # Core alert methods
    # ─────────────────────────────────────────

    async def alert_new_draft(
        self,
        headline: str,
        category: str,
        source_name: str,
        article_id: str,
        is_breaking: bool = False,
    ) -> bool:
        """
        Alert editors that a new AI draft is ready for review.
        Links directly to /Fnewsroom242/stories/[id] for one-tap access.
        """
        review_url = f"{settings.FRONTEND_URL}/Fnewsroom242/stories/{article_id}"
        priority_emoji = "🚨" if is_breaking else "📰"
        priority_label = "BREAKING — AI Draft Ready" if is_breaking else "New AI Draft Ready"

        text = (
            f"{priority_emoji} <b>{priority_label}</b>\n\n"
            f"📝 <b>{self._escape(headline)}</b>\n\n"
            f"🏷️ Category: <b>{self._escape(category)}</b>\n"
            f"📡 Source: {self._escape(source_name)}\n"
            f"🆔 ID: <code>{article_id}</code>\n\n"
            f"👉 <a href='{review_url}'>Open Article Editor</a>"
        )
        return await self.send_message(text)


    async def alert_breaking_story(self, headline: str, source: str, url: str) -> bool:
        """Alert staff about a breaking story detected from a high-priority source."""
        text = (
            "🚨 <b>BREAKING HEALTH STORY DETECTED</b>\n\n"
            f"📰 <b>{self._escape(headline)}</b>\n\n"
            f"📡 Source: {self._escape(source)}\n"
            f"🔗 <a href='{url}'>Read Original</a>"
        )
        return await self.send_message(text)

    async def alert_source_error(self, source_name: str, error: str) -> bool:
        """Alert about repeated source polling failures."""
        text = (
            "⚠️ <b>Source Polling Error</b>\n\n"
            f"📡 Source: {self._escape(source_name)}\n"
            f"❌ Error: {self._escape(error[:200])}"
        )
        return await self.send_message(text)

    async def alert_system_status(self, message: str) -> bool:
        """Send a system status notification (startup, shutdown, etc.)."""
        text = f"🔧 <b>Flobstar System</b>\n\n{self._escape(message)}"
        return await self.send_message(text)

    async def alert_poll_summary(
        self,
        drafts_saved: int,
        seen: int,
        elapsed: float,
    ) -> bool:
        """
        Send a periodic summary to the newsroom after a productive poll cycle.
        Only called when at least one draft was saved.
        """
        stories_url = f"{settings.FRONTEND_URL}/Fnewsroom242/stories"
        text = (
            "📊 <b>Flobstar Poller Summary</b>\n\n"
            f"✅ Drafts saved: <b>{drafts_saved}</b>\n"
            f"🔍 Articles scanned: {seen}\n"
            f"⏱️ Cycle time: {elapsed}s\n\n"
            f"👉 <a href='{stories_url}'>Review Drafts in Newsroom</a>"
        )
        return await self.send_message(text)

    async def alert_new_story(self, headline: str, source: str, priority: str) -> bool:
        """Alert staff about a new story awaiting review (legacy compat)."""
        emoji = {"breaking": "🚨", "important": "⚡", "routine": "📋"}.get(priority, "📋")
        text = (
            f"{emoji} <b>Story Detected</b>\n\n"
            f"📰 {self._escape(headline)}\n"
            f"📡 Source: {self._escape(source)}\n"
            f"🏷️ Priority: {priority.upper()}"
        )
        return await self.send_message(text)

    async def alert_ai_draft_ready(self, headline: str, story_id: str) -> bool:
        """Alert editors that an AI draft is ready (legacy compat)."""
        newsroom_url = f"{settings.FRONTEND_URL}/MedSense_Dashboard"
        text = (
            "🤖 <b>AI Draft Ready for Review</b>\n\n"
            f"📰 {self._escape(headline)}\n"
            f"🆔 Story ID: <code>{story_id}</code>\n\n"
            f"👉 <a href='{newsroom_url}'>Open Newsroom</a>"
        )
        return await self.send_message(text)

    async def test_connection(self) -> dict:
        """Test the Telegram bot connection by calling getMe."""
        if not self.enabled:
            return {"ok": False, "error": "Notifier not configured"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._url("getMe"))
                resp.raise_for_status()
                data = resp.json()
                if data.get("ok"):
                    bot = data["result"]
                    return {
                        "ok": True,
                        "bot_name": bot.get("first_name"),
                        "bot_username": bot.get("username"),
                        "chat_id": settings.TELEGRAM_CHAT_ID,
                    }
                return {"ok": False, "error": data.get("description", "Unknown error")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    @staticmethod
    def _escape(text: str) -> str:
        """Escape HTML special characters for Telegram HTML parse mode."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


# Global Telegram notifier instance
telegram = TelegramNotifier()
