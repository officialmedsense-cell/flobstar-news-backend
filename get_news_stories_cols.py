import asyncio
import asyncpg

async def get_cols():
    try:
        conn = await asyncpg.connect(
            host='db.ufiirgbphacmlcgszqdx.supabase.co',
            port=5432,
            database='postgres',
            user='postgres',
            password='Flobstar242',
            ssl='require'
        )
        rows = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'news_stories'
            ORDER BY ordinal_position;
        """)
        print("EXACT COLUMNS IN news_stories TABLE:")
        for r in rows:
            print(f"  - {r['column_name']} ({r['data_type']})")
        await conn.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(get_cols())
