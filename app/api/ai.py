"""
API endpoints for AI content generation
"""

import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import structlog

from app.core.database import get_db
from app.core.auth import require_service_role
from app.models.news_story import NewsStory
from app.models.ai_generation import AIGeneration
from app.services.ai_generator import ai_generator
from app.notifications.telegram import telegram

logger = structlog.get_logger()

router = APIRouter()


def _resolve_provider(provider: str) -> str:
    """Return provider or auto-select best available one."""
    if ai_generator.is_available(provider):
        return provider
    auto = ai_generator.get_default_provider()
    if auto:
        logger.warning(f"Provider '{provider}' not available, using '{auto}'")
        return auto
    raise HTTPException(
        status_code=503,
        detail="No AI providers configured. Add a MISTRAL_API_KEY to .env"
    )


@router.post("/generate-headline/{story_id}")
async def generate_headline(
    story_id: str,
    provider: str = "mistral",
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """Generate an AI headline for a story."""
    provider = _resolve_provider(provider)

    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    ai_gen = AIGeneration(
        story_id=story_id,
        generation_type="headline",
        model_used=provider,
        status="processing",
        input_prompt=f"Generate headline for: {story.original_headline}"
    )
    db.add(ai_gen)
    await db.commit()
    await db.refresh(ai_gen)

    t_start = time.time()
    try:
        generated_headline = await ai_generator.generate_headline(
            story.original_headline,
            story.original_content or "",
            provider
        )
        elapsed_ms = int((time.time() - t_start) * 1000)

        ai_gen.status = "completed"
        ai_gen.generated_headline = generated_headline
        ai_gen.processing_time_ms = elapsed_ms
        ai_gen.requires_human_review = True
        await db.commit()

        story.flobstar_headline = generated_headline
        story.ai_generated = True
        story.ai_generation_id = ai_gen.id
        await db.commit()

        logger.info("AI headline generated", story_id=story_id, provider=provider, elapsed_ms=elapsed_ms)

        return {
            "story_id": story_id,
            "original_headline": story.original_headline,
            "generated_headline": generated_headline,
            "ai_generation_id": str(ai_gen.id),
            "provider": provider,
            "processing_time_ms": elapsed_ms,
        }

    except Exception as e:
        logger.error("AI headline generation failed", story_id=story_id, error=str(e))
        ai_gen.status = "failed"
        ai_gen.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@router.post("/generate-summary/{story_id}")
async def generate_summary(
    story_id: str,
    max_length: int = 300,
    provider: str = "mistral",
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """Generate an AI summary for a story."""
    provider = _resolve_provider(provider)

    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    ai_gen = AIGeneration(
        story_id=story_id,
        generation_type="summary",
        model_used=provider,
        status="processing",
        input_prompt="Generate summary for story"
    )
    db.add(ai_gen)
    await db.commit()
    await db.refresh(ai_gen)

    t_start = time.time()
    try:
        generated_summary = await ai_generator.generate_summary(
            story.original_content or "",
            max_length,
            provider
        )
        elapsed_ms = int((time.time() - t_start) * 1000)

        ai_gen.status = "completed"
        ai_gen.generated_summary = generated_summary
        ai_gen.processing_time_ms = elapsed_ms
        ai_gen.requires_human_review = True
        await db.commit()

        story.flobstar_summary = generated_summary
        story.ai_generated = True
        story.ai_generation_id = ai_gen.id
        await db.commit()

        logger.info("AI summary generated", story_id=story_id, provider=provider, elapsed_ms=elapsed_ms)

        return {
            "story_id": story_id,
            "generated_summary": generated_summary,
            "ai_generation_id": str(ai_gen.id),
            "provider": provider,
            "processing_time_ms": elapsed_ms,
        }

    except Exception as e:
        logger.error("AI summary generation failed", story_id=story_id, error=str(e))
        ai_gen.status = "failed"
        ai_gen.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@router.post("/generate-article/{story_id}")
async def generate_article(
    story_id: str,
    provider: str = "mistral",
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """Generate a full AI article for a story."""
    provider = _resolve_provider(provider)

    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    ai_gen = AIGeneration(
        story_id=story_id,
        generation_type="full_article",
        model_used=provider,
        status="processing",
        input_prompt=f"Generate full article for: {story.original_headline}"
    )
    db.add(ai_gen)
    await db.commit()
    await db.refresh(ai_gen)

    t_start = time.time()
    try:
        generated_article = await ai_generator.generate_full_article(
            story.original_headline or "",
            story.original_content or "",
            story.category or "Health",
            provider
        )
        elapsed_ms = int((time.time() - t_start) * 1000)

        ai_gen.status = "completed"
        ai_gen.generated_content = generated_article
        ai_gen.processing_time_ms = elapsed_ms
        ai_gen.requires_human_review = True
        await db.commit()

        story.flobstar_content = generated_article
        story.ai_generated = True
        story.ai_generation_id = ai_gen.id
        story.status = "ai_draft_ready"
        await db.commit()

        logger.info("AI article generated", story_id=story_id, provider=provider, elapsed_ms=elapsed_ms)

        # Notify Telegram that a draft is ready
        await telegram.alert_ai_draft_ready(
            headline=story.flobstar_headline or story.original_headline or "Untitled",
            story_id=story_id
        )

        return {
            "story_id": story_id,
            "generated_article": generated_article,
            "ai_generation_id": str(ai_gen.id),
            "provider": provider,
            "processing_time_ms": elapsed_ms,
        }

    except Exception as e:
        logger.error("AI article generation failed", story_id=story_id, error=str(e))
        ai_gen.status = "failed"
        ai_gen.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@router.post("/fact-check/{story_id}")
async def fact_check(
    story_id: str,
    provider: str = "mistral",
    current_user: dict = Depends(require_service_role),
    db: AsyncSession = Depends(get_db)
):
    """Perform AI fact-checking on a story."""
    provider = _resolve_provider(provider)

    query = select(NewsStory).where(NewsStory.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        content = story.flobstar_content or story.original_content or ""
        t_start = time.time()
        fact_check_result = await ai_generator.fact_check(content, provider)
        elapsed_ms = int((time.time() - t_start) * 1000)

        story.requires_fact_check = bool(fact_check_result.get("issues_found"))
        await db.commit()

        logger.info(
            "AI fact-check completed",
            story_id=story_id,
            issues_found=fact_check_result.get("issues_found"),
            elapsed_ms=elapsed_ms
        )

        return {
            "story_id": story_id,
            "fact_check_result": fact_check_result,
            "provider": provider,
            "processing_time_ms": elapsed_ms,
        }

    except Exception as e:
        logger.error("AI fact-check failed", story_id=story_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Fact-check failed: {str(e)}")


@router.get("/status")
async def get_ai_status():
    """Get AI service availability status."""
    default = ai_generator.get_default_provider()
    return {
        "mistral_available": ai_generator.is_available("mistral"),
        "openai_available": ai_generator.is_available("openai"),
        "anthropic_available": ai_generator.is_available("anthropic"),
        "default_provider": default,
        "ready": default is not None,
    }


@router.get("/telegram/test")
async def test_telegram(current_user: dict = Depends(require_service_role)):
    """Test Telegram bot connection and send a test message."""
    connection = await telegram.test_connection()
    if connection.get("ok"):
        await telegram.alert_system_status(
            "✅ Flobstar News Intelligence backend is online and Telegram notifications are working!"
        )
    return connection
