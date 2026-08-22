import asyncio
import sys
from app.services.ai_generator import ai_generator
from app.core.database import AsyncSessionLocal
from app.models.news_story import NewsStory
from sqlalchemy import select

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def test_mistral_generation():
    print("=== TESTING MISTRAL AI ON REAL STORY ===")
    
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(NewsStory).limit(1))
        story = res.scalar_one_or_none()
        
        if not story:
            print("No stories found in database.")
            return

        print(f"\nOriginal Headline:\n  {story.original_title}")
        print(f"Source: {story.source_name}")
        print("\nCalling Mistral AI (mistral-large-latest) to generate optimized headline...")
        
        headline = await ai_generator.generate_headline(
            original_headline=story.original_title,
            original_content=story.original_content or story.original_summary or "",
            provider="mistral"
        )
        print(f"\n[GENERATED FLOBSTAR HEADLINE]:\n  {headline}")

        print("\nCalling Mistral AI to generate full draft article...")
        article = await ai_generator.generate_full_article(
            original_headline=story.original_title,
            original_content=story.original_content or story.original_summary or "",
            category=story.category or "Health Research",
            provider="mistral"
        )
        print(f"\n[GENERATED FLOBSTAR DRAFT ARTICLE - PREVIEW]:\n")
        print(article[:600] + "\n...")
        print(f"\nTotal Article Word Count: {len(article.split())} words")

asyncio.run(test_mistral_generation())
