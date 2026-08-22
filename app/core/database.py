"""
Database configuration and session management
Supports both REST-only mode (Render/Cloud) and direct PostgreSQL connection.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Base class for models
Base = declarative_base()

engine = None
AsyncSessionLocal = None

db_url = settings.database_url
if db_url and db_url.startswith("postgresql"):
    try:
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"ssl": "require"},
            future=True
        )
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    except Exception:
        engine = None
        AsyncSessionLocal = None


async def get_db():
    """
    Dependency for getting async database sessions if available.
    """
    if AsyncSessionLocal:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    else:
        yield None
