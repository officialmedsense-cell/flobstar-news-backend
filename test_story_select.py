import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.news_story import NewsStory

async def test_select():
    try:
        async with AsyncSessionLocal() as db:
            query = select(NewsStory).limit(5)
            res = await db.execute(query)
            stories = res.scalars().all()
            print("STORIES FOUND:", len(stories))
            for s in stories:
                print(" -", s.id, "|", s.original_title)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test_select())
