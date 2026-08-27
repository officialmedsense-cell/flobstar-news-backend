"""
AI Content Generation Service
Primary: Mistral AI (mistral-large-latest)
Fallback: OpenAI GPT-4, Anthropic Claude
"""

import time
import json
from typing import Optional, Dict, Any
import structlog
from mistralai.client import Mistral
from app.core.config import settings
from app.services.flobstar_system_prompt import (
    FLOBSTAR_SYSTEM_PROMPT,
    build_headline_user_message,
    build_summary_user_message,
    build_full_article_user_message,
    build_fact_check_user_message,
    validate_article_schema,
    sanitize_article_html,
    normalize_rss_category,
)

logger = structlog.get_logger()


def _is_valid_key(key: Optional[str]) -> bool:
    """Check if an API key is a real key (not a placeholder)."""
    return bool(
        key
        and len(key) > 10
        and not key.startswith("your_")
        and key != "sk-xxxx"
    )


class AIGenerator:
    """Service for AI-powered content generation (Mistral primary with multi-key failover)"""

    MISTRAL_MODELS = ["mistral-large-latest", "mistral-small-latest", "open-mistral-nemo"]

    def __init__(self):
        self.mistral_clients: list = []
        self.openai_client = None
        self.anthropic_client = None

        # Initialize Mistral clients (Primary & Fallback keys)
        keys = []
        if _is_valid_key(settings.MISTRAL_API_KEY):
            keys.append(settings.MISTRAL_API_KEY)
        if _is_valid_key(getattr(settings, "MISTRAL_API_KEY_FALLBACK", None)) and settings.MISTRAL_API_KEY_FALLBACK not in keys:
            keys.append(settings.MISTRAL_API_KEY_FALLBACK)

        for idx, key in enumerate(keys, 1):
            try:
                client = Mistral(api_key=key)
                self.mistral_clients.append(client)
                logger.info(f"Mistral client #{idx} initialized", key_prefix=f"{key[:6]}...")
            except Exception as e:
                logger.warning(f"Could not init Mistral client #{idx}", error=str(e))

        if not self.mistral_clients:
            logger.warning("No valid Mistral API keys configured")

        # Initialize OpenAI client (FALLBACK)
        if _is_valid_key(settings.OPENAI_API_KEY):
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized (fallback)")
            except ImportError:
                logger.warning("openai package not available")

        # Initialize Anthropic client (FALLBACK)
        if _is_valid_key(settings.ANTHROPIC_API_KEY):
            try:
                from anthropic import AsyncAnthropic
                self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized (fallback)")
            except ImportError:
                logger.warning("anthropic package not available")

    def is_available(self, provider: str = "mistral") -> bool:
        """Check if an AI provider is available."""
        if provider == "mistral":
            return len(self.mistral_clients) > 0
        elif provider == "openai":
            return self.openai_client is not None
        elif provider == "anthropic":
            return self.anthropic_client is not None
        return False

    def get_default_provider(self) -> Optional[str]:
        """Return the first available provider."""
        for p in ["mistral", "openai", "anthropic"]:
            if self.is_available(p):
                return p
        return None

    # ─────────────────────────────────────────
    # Public generation methods
    # ─────────────────────────────────────────

    async def generate_headline(
        self,
        original_headline: str,
        original_content: str,
        provider: str = "mistral"
    ) -> str:
        """Generate an optimized headline for a news story using Flobstar rules."""
        prompt = build_headline_user_message(original_headline, original_content)
        return await self._generate(prompt, provider, fallback=original_headline)

    async def generate_summary(
        self,
        original_content: str,
        max_length: int = 150,
        provider: str = "mistral"
    ) -> str:
        """Generate a concise summary/lead paragraph for news content."""
        prompt = build_summary_user_message(original_content, max_words=max_length)
        return await self._generate(prompt, provider, fallback=original_content[:max_length])

    async def generate_full_article(
        self,
        original_headline: str,
        original_content: str,
        category: str = "Health",
        provider: str = "mistral"
    ) -> str:
        """Generate a full article based on source content using Flobstar standards."""
        prompt = build_full_article_user_message(
            original_headline=original_headline,
            original_content=original_content,
            category=category
        )
        response = await self._generate(prompt, provider, fallback=original_content)
        if not response:
            return sanitize_article_html(original_content)

        try:
            clean_json = response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_json)
            is_valid, errors, sanitized_data = validate_article_schema(parsed)
            if is_valid and sanitized_data:
                return sanitized_data["article"]
            logger.warning("AI article schema validation warning", errors=errors)
            if isinstance(parsed, dict) and parsed.get("article"):
                return sanitize_article_html(str(parsed["article"]))
        except json.JSONDecodeError:
            pass

    async def generate_unified_story(
        self,
        *,
        original_headline: str,
        original_content: str,
        category: str = "Health",
        author: str = "Flobstar News",
        source_name: str = "News Wire",
        source_url: str = "N/A",
        source_type: str = "secondary",
        provider: str = "mistral"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a complete unified Flobstar News story in ONE single AI call.
        Returns a dict with: headline, seo_title, meta_description, category, visual_keyword, article
        """
        prompt = build_full_article_user_message(
            original_headline=original_headline,
            original_content=original_content,
            category=category,
            author=author,
            source_url=source_url,
            source_name=source_name,
            source_type=source_type,
        )
        response = await self._generate(prompt, provider, fallback=None)
        if not response:
            return None

        try:
            clean_json = response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_json)
            is_valid, errors, sanitized_data = validate_article_schema(parsed)
            if is_valid and sanitized_data:
                return sanitized_data

            logger.warning("AI article schema validation warning", errors=errors)
            if isinstance(parsed, dict) and parsed.get("article"):
                return {
                    "headline": parsed.get("headline") or original_headline,
                    "seo_title": parsed.get("seo_title") or original_headline,
                    "meta_description": parsed.get("meta_description") or "",
                    "category": normalize_rss_category(parsed.get("category") or category),
                    "visual_keyword": parsed.get("visual_keyword") or "",
                    "article": sanitize_article_html(str(parsed["article"])),
                }
        except json.JSONDecodeError as e:
            logger.error("JSON decode error in AI unified story response", error=str(e))

        return None

    async def fact_check(
        self,
        content: str,
        provider: str = "mistral"
    ) -> Dict[str, Any]:
        """Perform fact-checking on content."""
        prompt = build_fact_check_user_message(content)
        response = await self._generate(prompt, provider, fallback=None)
        if response:
            try:
                # Strip code fences if present
                clean_json = response.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_json)
            except json.JSONDecodeError:
                logger.error("Failed to parse fact-check JSON response")
        return {"issues_found": False, "confidence_score": 0.5, "notes": "Parse error"}

    # ─────────────────────────────────────────
    # Internal generation methods
    # ─────────────────────────────────────────

    async def _generate(
        self,
        prompt: str,
        provider: str,
        fallback: Optional[str] = None
    ) -> Optional[str]:
        """Route to the correct provider, with automatic fallback."""
        # Auto-select if provider not available
        if not self.is_available(provider):
            auto = self.get_default_provider()
            if auto:
                logger.warning(
                    f"Provider '{provider}' not available, using '{auto}'",
                    requested=provider,
                    using=auto
                )
                provider = auto
            else:
                logger.error("No AI providers available")
                return fallback

        try:
            if provider == "mistral":
                return await self._generate_with_mistral(prompt)
            elif provider == "openai":
                return await self._generate_with_openai(prompt)
            elif provider == "anthropic":
                return await self._generate_with_anthropic(prompt)
        except Exception as e:
            logger.error(f"AI generation failed with {provider}", error=str(e))
            return fallback

        return fallback

    async def _generate_with_mistral(self, prompt: str) -> str:
        """Generate content using Mistral AI with multi-key failover and resilient fallback models."""
        last_error = None
        for client_idx, client in enumerate(self.mistral_clients):
            for model_name in self.MISTRAL_MODELS:
                try:
                    response = await client.chat.complete_async(
                        model=model_name,
                        max_tokens=2500,
                        messages=[
                            {
                                "role": "system",
                                "content": FLOBSTAR_SYSTEM_PROMPT
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    )
                    content = response.choices[0].message.content
                    if content and content.strip():
                        return content.strip()
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Mistral attempt failed, trying next client/model",
                        client_index=client_idx,
                        model=model_name,
                        error=str(e)[:120]
                    )
                    continue

        if last_error:
            raise last_error
        raise RuntimeError("All Mistral clients and models exhausted")

    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate content using OpenAI (fallback)."""
        response = await self.openai_client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": FLOBSTAR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()

    async def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate content using Anthropic (fallback)."""
        response = await self.anthropic_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            system=FLOBSTAR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()


# Global AI generator instance
ai_generator = AIGenerator()
